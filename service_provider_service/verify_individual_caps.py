import os
import sys
import django
import uuid

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from service_provider.role_capabilities import get_default_capabilities, ALL_VETERINARY_CAPABILITIES

def verify_individual_capabilities():
    print("\n🔹 Verifying Individual Capabilities Assignment...")
    
    # 1. Test get_default_capabilities directly
    print("   Testing get_default_capabilities('individual')...")
    caps = get_default_capabilities("individual")
    
    if set(caps) == set(ALL_VETERINARY_CAPABILITIES):
        print("   ✅ SUCCESS: 'individual' role returns ALL capabilities.")
    else:
        print(f"   ❌ FAILED: Expected {len(ALL_VETERINARY_CAPABILITIES)} capabilities, got {len(caps)}.")
        print(f"   Missing: {set(ALL_VETERINARY_CAPABILITIES) - set(caps)}")
        return

    # 2. Simulate User Creation (Mocking Kafka Consumer Logic)
    print("   Simulating VerifiedUser creation for Individual...")
    auth_user_id = uuid.uuid4()
    role = "individual"
    
    user, created = VerifiedUser.objects.update_or_create(
        auth_user_id=auth_user_id,
        defaults={
            "full_name": "Test Individual Vet",
            "email": "individual_vet@test.com",
            "role": role,
            "permissions": get_default_capabilities(role),
        },
    )
    
    print(f"   Created User: {user.email} with Role: {user.role}")
    print(f"   Assigned Permissions: {user.permissions}")
    
    if set(user.permissions) == set(ALL_VETERINARY_CAPABILITIES):
        print("   ✅ SUCCESS: Database record has ALL capabilities.")
    else:
        print("   ❌ FAILED: Database record missing capabilities.")

    # Cleanup
    user.delete()

if __name__ == "__main__":
    verify_individual_capabilities()
