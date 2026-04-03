import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, AllowedService, VerifiedUser

def seed_services():
    print("--- Seeding Services for Active Providers ---")
    providers = ServiceProvider.objects.filter(profile_status='active')
    
    # Common services to assign
    services_to_assign = [
        {"name": "General Consultation", "icon": "tabler-stethoscope"},
        {"name": "Pet Grooming", "icon": "tabler-scissors"},
        {"name": "Vaccination", "icon": "tabler-vaccine"},
    ]
    
    for p in providers:
        user = p.verified_user
        print(f"Seeding services for {user.full_name}...")
        
        for s_data in services_to_assign:
            # Generate a random UUID for service_id since it's just for display in marketplace
            AllowedService.objects.get_or_create(
                verified_user=user,
                name=s_data['name'],
                defaults={
                    'service_id': uuid.uuid4(),
                    'icon': s_data['icon']
                }
            )
            print(f"  - Added service: {s_data['name']}")

    print("\nSeeding complete.")

if __name__ == "__main__":
    seed_services()
