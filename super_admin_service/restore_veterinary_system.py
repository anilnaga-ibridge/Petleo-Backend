import os
import sys
import django

# Setup Django Environment
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_services.models import Service
from dynamic_categories.models import Category
from plans_coupens.models import BillingCycleConfig

def restore_system():
    print("🚀 Starting Veterinary System Meta-Data Restoration...")

    # 1. Restore Billing Cycles
    print("\n💳 Restoring Billing Cycles...")
    cycles = [
        {"code": "MONTHLY", "display_name": "Monthly", "duration_days": 30, "is_active": True},
        {"code": "YEARLY", "display_name": "Yearly", "duration_days": 365, "is_active": True},
        {"code": "QUARTERLY", "display_name": "Quarterly", "duration_days": 90, "is_active": True}
    ]
    for cycle_data in cycles:
        obj, created = BillingCycleConfig.objects.update_or_create(
            code=cycle_data["code"],
            defaults=cycle_data
        )
        print(f"{'✅ Created' if created else '🔄 Updated'}: Billing Cycle {obj.code}")

    # 2. Restore Veterinary Service
    print("\n🏥 Restoring Veterinary Service...")
    vet_service, created = Service.objects.update_or_create(
        name='VETERINARY',
        defaults={
            'display_name': 'Veterinary Management',
            'icon': 'tabler-stethoscope',
            'is_active': True
        }
    )
    print(f"{'✅ Created' if created else '🔄 Updated'}: Service VETERINARY")

    # 3. Restore Veterinary Categories (Capabilities)
    print("\n📂 Restoring Veterinary Categories...")
    categories = [
        {"name": "Veterinary Core", "linked_capability": "VETERINARY_CORE"},
        {"name": "Visits", "linked_capability": "VETERINARY_VISITS"},
        {"name": "Patients", "linked_capability": "VETERINARY_PATIENTS"},
        {"name": "Veterinary Assistant", "linked_capability": "VETERINARY_VITALS"},
        {"name": "Doctor Station", "linked_capability": "VETERINARY_DOCTOR"},
        {"name": "Pharmacy", "linked_capability": "VETERINARY_PHARMACY"},
        {"name": "Pharmacy Store", "linked_capability": "VETERINARY_PHARMACY_STORE"},
        {"name": "Labs", "linked_capability": "VETERINARY_LABS"},
        {"name": "Schedule", "linked_capability": "VETERINARY_SCHEDULE"},
        {"name": "Online Consult", "linked_capability": "VETERINARY_ONLINE_CONSULT"},
        {"name": "Offline Visits", "linked_capability": "VETERINARY_OFFLINE_VISIT"},
        {"name": "Medicine Reminders", "linked_capability": "VETERINARY_MEDICINE_REMINDERS"},
        {"name": "Clinic Settings", "linked_capability": "VETERINARY_ADMIN_SETTINGS"},
        {"name": "Metadata Management", "linked_capability": "VETERINARY_METADATA"},
    ]
    for cat_data in categories:
        obj, created = Category.objects.update_or_create(
            service=vet_service,
            linked_capability=cat_data["linked_capability"],
            defaults={
                "name": cat_data["name"],
                "is_active": True
            }
        )
        print(f"{'✅ Created' if created else '🔄 Updated'}: Category {obj.name} ({obj.linked_capability})")

    print("\n✨ Restoration Complete. You can now rebuild your plans in the Dashboard.")

if __name__ == "__main__":
    restore_system()
