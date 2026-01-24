import os
import django
import psycopg2
from decimal import Decimal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import (
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility,
    ProviderTemplatePricing
)
from service_provider.models import AllowedService, VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess

def sync_from_super_admin():
    print("🚀 Starting sync from Super Admin DB...")
    
    # 1. Connect to Super Admin Postgres
    try:
        conn = psycopg2.connect(
            dbname="Super_Admin",
            user="petleo",
            password="petleo",
            host="127.0.0.1",
            port="5432"
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Failed to connect to Super Admin DB: {e}")
        return

    # 2. Sync Services
    print("📦 Syncing Services...")
    cur.execute("SELECT id, name, display_name FROM dynamic_services_service")
    services = cur.fetchall()
    for s_id, name, d_name in services:
        ProviderTemplateService.objects.update_or_create(
            super_admin_service_id=str(s_id),
            defaults={
                "name": name,
                "display_name": d_name,
                "icon": "tabler-stethoscope" if "VET" in name.upper() else "tabler-box"
            }
        )
    print(f"✅ Synced {len(services)} services.")

    # 3. Sync Categories
    print("📂 Syncing Categories...")
    cur.execute("SELECT id, service_id, name, linked_capability FROM dynamic_categories_category")
    categories = cur.fetchall()
    for c_id, s_id, name, linked_cap in categories:
        try:
            svc = ProviderTemplateService.objects.get(super_admin_service_id=str(s_id))
            ProviderTemplateCategory.objects.update_or_create(
                super_admin_category_id=str(c_id),
                defaults={
                    "service": svc,
                    "name": name,
                    "linked_capability": linked_cap
                }
            )
        except ProviderTemplateService.DoesNotExist:
            print(f"⚠️ Service {s_id} not found for category {name}")
    print(f"✅ Synced {len(categories)} categories.")

    # 4. Sync Facilities
    print("🏢 Syncing Facilities...")
    cur.execute("SELECT id, service_id, name, description FROM dynamic_facilities_facility")
    facilities = cur.fetchall()
    for f_id, s_id, name, desc in facilities:
        try:
            # Find a category for this service as ProviderTemplateFacility requires it
            cat = ProviderTemplateCategory.objects.filter(service__super_admin_service_id=str(s_id)).first()
            if not cat:
                print(f"⚠️ No category found for service {s_id}, skipping facility {name}")
                continue
                
            ProviderTemplateFacility.objects.update_or_create(
                super_admin_facility_id=str(f_id),
                defaults={
                    "category": cat,
                    "name": name,
                    "description": desc
                }
            )
        except Exception as e:
            print(f"❌ Error syncing facility {name}: {e}")
    print(f"✅ Synced {len(facilities)} facilities.")

    # 5. Sync Pricing
    print("💰 Syncing Pricing...")
    cur.execute("SELECT id, service_id, category_id, facility_id, base_price, duration_minutes FROM dynamic_pricing_pricingrule")
    pricing = cur.fetchall()
    for p_id, s_id, c_id, f_id, price, duration in pricing:
        try:
            svc = ProviderTemplateService.objects.get(super_admin_service_id=str(s_id))
            cat = ProviderTemplateCategory.objects.filter(super_admin_category_id=str(c_id)).first() if c_id else None
            fac = ProviderTemplateFacility.objects.filter(super_admin_facility_id=str(f_id)).first() if f_id else None
            
            ProviderTemplatePricing.objects.update_or_create(
                super_admin_pricing_id=str(p_id),
                defaults={
                    "service": svc,
                    "category": cat,
                    "facility": fac,
                    "price": price,
                    "duration": str(duration) if duration else "Fixed",
                    "description": "Synced from Super Admin"
                }
            )
        except Exception as e:
            print(f"❌ Error syncing pricing {p_id}: {e}")
    print(f"✅ Synced {len(pricing)} pricing rules.")

    # 6. Populate AllowedService for Employees
    print("🔧 Repairing AllowedService for Employees...")
    # Find all users who have capabilities
    employees = VerifiedUser.objects.all()
    
    repaired_count = 0
    for emp in employees:
        caps = ProviderCapabilityAccess.objects.filter(user=emp)
        if caps.exists():
            # Clear and rebuild
            AllowedService.objects.filter(verified_user=emp).delete()
            
            seen_services = set()
            for cap in caps:
                if cap.service_id and cap.service_id not in seen_services:
                    try:
                        # Validate if it's a UUID
                        import uuid as uuid_pkg
                        try:
                            uuid_pkg.UUID(str(cap.service_id))
                        except ValueError:
                            print(f"⏩ Skipping non-UUID service_id: {cap.service_id}")
                            continue

                        tmpl = ProviderTemplateService.objects.get(super_admin_service_id=cap.service_id)
                        AllowedService.objects.create(
                            verified_user=emp,
                            service_id=cap.service_id,
                            name=tmpl.display_name,
                            icon=tmpl.icon
                        )
                        seen_services.add(cap.service_id)
                    except ProviderTemplateService.DoesNotExist:
                        print(f"⚠️ Template not found for service_id: {cap.service_id}")
                    except Exception as e:
                        print(f"❌ Error creating AllowedService for {emp.email}: {e}")
            repaired_count += 1
            
    print(f"✅ Repaired AllowedService for {repaired_count} users.")

    cur.close()
    conn.close()
    print("🎉 Sync Completed!")

if __name__ == "__main__":
    sync_from_super_admin()
