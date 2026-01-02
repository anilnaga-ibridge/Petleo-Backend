import os
import sys
import django
# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from users.views import UserViewSet
from users.models import User, Role

def verify_visibility():
    print("\n🔹 Verifying User Visibility...")
    factory = APIRequestFactory()
    view = UserViewSet.as_view({'get': 'list'})

    # 1. Create Super Admin
    super_admin, _ = User.objects.get_or_create(
        username="super_admin_test",
        defaults={
            "email": "super@test.com",
            "phone_number": "9999999999",
            "is_superuser": True,
            "is_active": True
        }
    )
    # Ensure is_superuser is True (if retrieved)
    if not super_admin.is_superuser:
        super_admin.is_superuser = True
        super_admin.save()

    # 2. Create Regular User
    role, _ = Role.objects.get_or_create(name="Individual")
    user, _ = User.objects.get_or_create(
        username="regular_user_test",
        defaults={
            "email": "regular@test.com",
            "phone_number": "8888888888",
            "role": role,
            "is_active": True
        }
    )

    # 3. Test Super Admin Visibility
    print("   Testing Super Admin Visibility...")
    request = factory.get('/auth/users/')
    force_authenticate(request, user=super_admin)
    response = view(request)
    
    if response.status_code == 200:
        count = len(response.data)
        print(f"   ✅ Super Admin sees {count} users.")
        if count >= 2:
             print("   ✅ SUCCESS: Super Admin sees multiple users.")
        else:
             print("   ⚠️ WARNING: Super Admin sees only 1 user (expected >= 2).")
    else:
        print(f"   ❌ FAILED: Super Admin request failed {response.status_code}")

    # Cleanup
    # super_admin.delete() # Keep for manual testing if needed, or delete
    # user.delete()

if __name__ == "__main__":
    verify_visibility()
