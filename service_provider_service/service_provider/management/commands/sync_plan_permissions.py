"""
Management command: sync_plan_permissions

Manually re-syncs the ProviderCapabilityAccess and related permission
tables for a provider by reading plan data from the super admin DB directly.

Usage:
    python manage.py sync_plan_permissions --email madhu@gmail.com
    python manage.py sync_plan_permissions --all
"""
import sys
import os
import django
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Re-sync plan permissions for a provider from super admin database (bypasses Kafka)"

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email of the provider to sync')
        parser.add_argument('--all', action='store_true', help='Re-sync ALL providers with active plans')

    def handle(self, *args, **options):
        email = options.get('email')
        sync_all = options.get('all')

        if not email and not sync_all:
            self.stderr.write("❌ Provide --email <email> or --all")
            return

        # Import super admin models via a secondary DB connection
        super_admin_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', '..', '..', '..', '..', 'super_admin_service'
        )
        super_admin_path = os.path.normpath(super_admin_path)

        if super_admin_path not in sys.path:
            sys.path.insert(0, super_admin_path)

        # Set Django to use super admin settings temporarily to get SA models
        orig_settings = os.environ.get('DJANGO_SETTINGS_MODULE')

        # --- Import provider service models ---
        from service_provider.models import VerifiedUser, AllowedService, Capability, ProviderCapability
        from provider_dynamic_fields.models import (
            ProviderCapabilityAccess, ProviderTemplateService,
            ProviderTemplateCategory, ProviderTemplateFacility
        )

        # Build queryset of users to sync
        qs = VerifiedUser.objects.all()
        if email:
            qs = qs.filter(email=email)
            if not qs.exists():
                self.stderr.write(f"❌ No user found with email: {email}")
                return

        synced = 0
        errors = 0

        for vu in qs:
            active_sub = vu.purchased_plans.filter(is_active=True).first()
            if not active_sub:
                if email:  # Only warn if explicitly targeted
                    self.stderr.write(f"⚠️  {vu.email}: No active subscription")
                continue

            self.stdout.write(f"🔄 Syncing: {vu.email} | Plan: {active_sub.plan_title}")

            try:
                with transaction.atomic():
                    # Fetch plan capability data from Super Admin via HTTP API
                    import requests
                    response = requests.get(
                        f"http://127.0.0.1:8000/api/plans/{active_sub.plan_id}/capabilities/",
                        timeout=10
                    )

                    if not response.ok:
                        # Try alternate endpoint
                        response = requests.get(
                            f"http://127.0.0.1:8000/api/superadmin/plan-capabilities/?plan_id={active_sub.plan_id}",
                            timeout=10
                        )

                    if response.ok:
                        data = response.json()
                        capabilities = data.get('capabilities', data.get('results', []))
                        self._sync_user_caps(vu, active_sub, capabilities)
                        self.stdout.write(f"   ✅ Synced via API: {len(capabilities)} capability records")
                        synced += 1
                    else:
                        self.stdout.write(f"   ⚠️  API returned {response.status_code}. Trying direct DB sync...")
                        self._sync_from_super_admin_db(vu, active_sub, super_admin_path)
                        synced += 1

            except Exception as e:
                self.stderr.write(f"   ❌ Error syncing {vu.email}: {e}")
                import traceback
                self.stderr.write(traceback.format_exc())
                errors += 1

        self.stdout.write(f"\n🏁 Done. Synced: {synced} | Errors: {errors}")

    def _sync_user_caps(self, vu, active_sub, capabilities):
        """Sync capabilities from a list of capability dicts."""
        from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService, ProviderTemplateCategory
        from service_provider.models import AllowedService, Capability, ProviderCapability

        ProviderCapabilityAccess.objects.filter(user=vu).delete()
        seen_services = set()

        for cap in capabilities:
            service_id = cap.get('service_id')
            category_id = cap.get('category_id')

            ProviderCapabilityAccess.objects.create(
                user=vu,
                plan_id=str(active_sub.plan_id),
                service_id=str(service_id) if service_id else None,
                category_id=str(category_id) if category_id else None,
                facility_id=str(cap.get('facility_id')) if cap.get('facility_id') else None,
                pricing_id=str(cap.get('pricing_id')) if cap.get('pricing_id') else None,
                can_view=bool(cap.get('can_view', True)),
                can_create=bool(cap.get('can_create', False)),
                can_edit=bool(cap.get('can_edit', False)),
                can_delete=bool(cap.get('can_delete', False)),
            )

            if service_id:
                seen_services.add(str(service_id))

        # Sync AllowedService
        AllowedService.objects.filter(verified_user=vu).delete()
        for s_id in seen_services:
            svc_tmpl = ProviderTemplateService.objects.filter(super_admin_service_id=s_id).first()
            name = svc_tmpl.display_name if svc_tmpl else s_id
            icon = svc_tmpl.icon if svc_tmpl else 'tabler-box'
            AllowedService.objects.update_or_create(
                verified_user=vu, service_id=s_id,
                defaults={"name": name, "icon": icon}
            )

        # Sync ProviderCapability (dynamic_capabilities)
        ProviderCapability.objects.filter(user=vu).delete()
        for s_id in seen_services:
            svc_tmpl = ProviderTemplateService.objects.filter(super_admin_service_id=s_id).first()
            cap_key = svc_tmpl.name.upper() if svc_tmpl else s_id.upper()
            cap_obj, _ = Capability.objects.get_or_create(
                key=cap_key, defaults={"label": cap_key.replace('_', ' ').title()}
            )
            ProviderCapability.objects.get_or_create(user=vu, capability=cap_obj, defaults={"is_active": True})

    def _sync_from_super_admin_db(self, vu, active_sub, super_admin_path):
        """
        Fallback: Import super admin models directly and read plan capability data.
        This is used when the API is not available.
        """
        os.environ['DJANGO_SETTINGS_MODULE'] = 'super_admin_service.settings'

        try:
            import django as sa_django
            sa_django.setup()
        except RuntimeError:
            pass  # Already setup

        from plans_coupens.models import ProviderPlanCapability as SAProviderPlanCapability

        # Find the matching user and plan in super admin DB
        try:
            from django.contrib.auth import get_user_model
            SAUser = get_user_model()
            sa_user = SAUser.objects.filter(email=vu.email).first()
            if not sa_user:
                self.stderr.write(f"   ❌ Super admin user not found for email: {vu.email}")
                return

            perms = SAProviderPlanCapability.objects.filter(
                user=sa_user,
                plan__id=active_sub.plan_id
            ).select_related('service', 'category', 'facility', 'plan')

            capabilities = []
            for p in perms:
                capabilities.append({
                    'service_id': str(p.service.id) if p.service else None,
                    'category_id': str(p.category.id) if p.category else None,
                    'facility_id': str(p.facility.id) if p.facility else None,
                    'pricing_id': None,
                    'can_view': bool((p.permissions or {}).get('can_view', True)),
                    'can_create': bool((p.permissions or {}).get('can_create', False)),
                    'can_edit': bool((p.permissions or {}).get('can_edit', False)),
                    'can_delete': bool((p.permissions or {}).get('can_delete', False)),
                })

            self._sync_user_caps(vu, active_sub, capabilities)
            self.stdout.write(f"   ✅ Synced from Super Admin DB: {len(capabilities)} capability records")

        except Exception as e:
            raise Exception(f"Direct DB sync failed: {e}")
