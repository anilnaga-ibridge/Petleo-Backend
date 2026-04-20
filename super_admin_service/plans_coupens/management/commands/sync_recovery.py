
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from admin_core.models import VerifiedUser, ProviderBillingProfile
from plans_coupens.models import PurchasedPlan, LegacyEntitlementRecovery, Invoice
from plans_coupens.billing_service import EntitlementOrchestrator, MigrationRecordGenerator
from plans_coupens.pdf_engine import PDFEngine

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Identifies and reconciles legacy B2B plans missing synchronization artifacts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting Production-Safe Sync Recovery..."))
        
        # 1. Detection Logic: 
        # - Currently Active (entitlement-wise)
        # - Has no Invoice (The core artifact of the new system)
        # - Has not been reconciled yet
        # - Status is ACTIVE or PENDING (for legacy data that was never fulfilled but granted access)
        legacy_plans = PurchasedPlan.objects.filter(
            is_active=True,
            invoice__isnull=True,
            is_legacy_reconciled=False
        ).exclude(status__in=['CANCELLED', 'EXPIRED'])

        if not legacy_plans.exists():
            self.stdout.write(self.style.SUCCESS("✅ No unreconciled legacy plans found."))
            return

        total = legacy_plans.count()
        success_count = 0
        skip_count = 0

        for plan in legacy_plans:
            try:
                # [ENHANCEMENT] Try to find a better display name/email from the VerifiedUser table
                display_email = plan.user.email
                if display_email.startswith('auto_'):
                    real_user = VerifiedUser.objects.filter(auth_user_id=plan.user.auth_user_id).first()
                    if real_user and real_user.email:
                        display_email = f"{real_user.email} (Auth ID: {plan.user.auth_user_id[:8]})"
                
                self.stdout.write(f"🔍 Processing plan {plan.id} for {display_email}...")
                
                with transaction.atomic():
                    # 2. Ensure Billing Profile exists (Requirement for sync payload)
                    billing_profile, created = ProviderBillingProfile.objects.get_or_create(
                        verified_user_id=plan.user.auth_user_id,
                        defaults={
                            "legal_name": getattr(plan.user, 'full_name', 'Legacy Provider'),
                            "billing_address": "MIGRATED_LEGACY_ADDRESS",
                            "billing_state": "MIGRATED",
                            "billing_state_code": "XX",
                            "is_incomplete": True,
                            "source": "RECOVERY"
                        }
                    )
                    
                    if created:
                        self.stdout.write(self.style.WARNING(f"  ⚠️ Created skeleton billing profile for {plan.user.email}"))

                    # 3. Idempotency: Ensure no existing recovery
                    if LegacyEntitlementRecovery.objects.filter(purchased_plan=plan).exists():
                        self.stdout.write(self.style.NOTICE(f"  ⏭️ Already has recovery record. Marking as reconciled."))
                        plan.is_legacy_reconciled = True
                        plan.save(update_fields=["is_legacy_reconciled"])
                        skip_count += 1
                        continue

                    # 4. Create Recovery Record & Generate MR Number
                    mr_number = MigrationRecordGenerator.get_next_number()
                    recovery = LegacyEntitlementRecovery.objects.create(
                        purchased_plan=plan,
                        migration_record_number=mr_number,
                        reason="Standard production-safe reconciliation for legacy entitlement."
                    )
                    
                    # 5. Generate Migration Record PDF (Audit-safe, no tax)
                    PDFEngine.generate_migration_record_pdf(recovery.id)

                    # 6. Mark Plan as Reconciled
                    plan.is_legacy_reconciled = True
                    plan.entitlement_source = "MIGRATION"
                    plan.save(update_fields=["is_legacy_reconciled", "entitlement_source"])

                    # 7. Trigger Sync (Decoupled from Invoice)
                    success, msg = EntitlementOrchestrator.trigger_sync(plan, reason="LEGACY_RECOVERY")
                    
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"  ✅ Reconciled & Synced: {mr_number}"))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"  ❌ Sync Error: {msg}"))
                        # We don't roll back the DB transaction for Kafka errors 
                        # to keep the local reconciliation state.
            
            except Exception as e:
                logger.exception(f"Fatal error during recovery of plan {plan.id}: {e}")
                self.stdout.write(self.style.ERROR(f"  💥 Fatal error: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"\n✨ Recovery Complete: {success_count} success, {skip_count} skipped, {total} total."))
