import os
import sys
import django

# Add current path and Auth Service paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.abspath(os.path.join(current_dir, '..')))
sys.path.append(os.path.abspath(os.path.join(current_dir, '..', 'Auth_Service', 'auth_service')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_services.models import Service
from dynamic_categories.models import Category

def seed_vet_taxonomy():
    # 1. Create/Get Veterinary Service
    print("🏥 Synchronizing Veterinary Service...")
    vet_service, created = Service.objects.update_or_create(
        name='VETERINARY',
        defaults={
            'display_name': 'Veterinary Management',
            'icon': 'tabler-stethoscope',
            'is_active': True
        }
    )
    if created:
        print("✅ Created Service: VETERINARY")
    else:
        print("🔄 Updated Service: VETERINARY")

    # 2. Define Categories from the Capability List
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

    print("\n📂 Synchronizing Categories...")
    for cat_data in categories:
        obj, created = Category.objects.update_or_create(
            service=vet_service,
            linked_capability=cat_data["linked_capability"],
            defaults={
                "name": cat_data["name"],
                "is_active": True
            }
        )
        if created:
            print(f"✅ Created Category: {obj.name} ({obj.linked_capability})")
        else:
            print(f"🔄 Updated Category: {obj.name} ({obj.linked_capability})")

    print("\n✨ Veterinary Taxonomy Synchronization Complete.")

if __name__ == "__main__":
    seed_vet_taxonomy()
