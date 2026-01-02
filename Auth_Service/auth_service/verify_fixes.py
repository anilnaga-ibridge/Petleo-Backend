import os
import sys
import django
# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from users.views import RegisterView, UserViewSet
from users.models import User, Role
from users.serializers import UserUpdateSerializer

def verify_security_fix():
    print("\n🔹 Verifying Security Fix (RegisterView)...")
    factory = APIRequestFactory()
    view = RegisterView.as_view()

    # Ensure roles exist
    doctor_role, _ = Role.objects.get_or_create(name="Doctor")
    org_role, _ = Role.objects.get_or_create(name="Organization")
    ind_role, _ = Role.objects.get_or_create(name="Individual")

    # 1. Unauthenticated Registration with Doctor Role ID (Should Fail)
    print(f"   Testing Unauthenticated Registration with Role ID {doctor_role.id} (Doctor)...")
    data = {
        "phone_number": "9999999901",
        "full_name": "Test Doctor",
        "email": "doctor@test.com",
        "role": doctor_role.id # Passing ID to test the resolution logic
    }
    request = factory.post('/api/auth/register/', data, format='json')
    response = view(request)
    
    if response.status_code == 403:
        print("   ✅ SUCCESS: Unauthenticated request rejected (403).")
    else:
        print(f"   ❌ FAILED: Expected 403, got {response.status_code}. Response: {response.data}")

    # 2. Authenticated as Individual (Should Fail)
    print("   Testing Authenticated (Individual) Registration with Doctor Role ID...")
    individual_user = User.objects.create(
        username="ind_user", 
        phone_number="9999999902", 
        role=ind_role,
        is_active=True
    )
    request = factory.post('/api/auth/register/', data, format='json')
    force_authenticate(request, user=individual_user)
    response = view(request)

    if response.status_code == 403:
        print("   ✅ SUCCESS: Non-Org user request rejected (403).")
    else:
        print(f"   ❌ FAILED: Expected 403, got {response.status_code}. Response: {response.data}")

    # Cleanup
    individual_user.delete()


def verify_serializer_fix():
    print("\n🔹 Verifying Serializer Fix (UserUpdateSerializer)...")
    
    role, _ = Role.objects.get_or_create(name="Individual")
    user = User.objects.create(
        username="serializer_test_user",
        phone_number="9999999903",
        role=role,
        is_active=True
    )
    
    serializer = UserUpdateSerializer(user)
    data = serializer.data
    
    print(f"   Serialized Data Keys: {list(data.keys())}")
    
    if 'is_active' in data and 'is_verified' in data:
        print("   ✅ SUCCESS: 'is_active' and 'is_verified' fields are present.")
        print(f"   is_active: {data['is_active']}, is_verified: {data['is_verified']}")
    else:
        print("   ❌ FAILED: Missing 'is_active' or 'is_verified' fields.")

    # Cleanup
    user.delete()

if __name__ == "__main__":
    try:
        verify_security_fix()
        verify_serializer_fix()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
