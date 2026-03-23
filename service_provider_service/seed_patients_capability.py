import os
import django

# Set up Django environment for service_provider_service
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import Capability, FeatureModule

def seed_patients_capability():
    print("🚀 Seeding VETERINARY_PATIENTS capability...")

    # 1. Create Capability
    cap, created = Capability.objects.get_or_create(
        key="VETERINARY_PATIENTS",
        defaults={
            "label": "Patients",
            "description": "Access to patient clinical records and history",
            "group": "General"
        }
    )
    print(f"✅ Capability 'VETERINARY_PATIENTS': {'Created' if created else 'Already Exists'}")

    # 2. Update FeatureModule if it exists (Patients)
    # The route for patients is 'veterinary-pets'
    feature = FeatureModule.objects.filter(route='veterinary-pets').first()
    if feature:
        feature.capability = cap
        feature.save()
        print(f"🔗 Linked FeatureModule '{feature.name}' to VETERINARY_PATIENTS")
    else:
        # Create it if missing
        FeatureModule.objects.get_or_create(
            key="VETERINARY_PATIENTS",
            defaults={
                "name": "Patients",
                "route": "veterinary-pets",
                "icon": "tabler-paw",
                "sequence": 20,
                "capability": cap,
                "is_active": True
            }
        )
        print("✨ Created FeatureModule 'Patients'")

if __name__ == "__main__":
    seed_patients_capability()
