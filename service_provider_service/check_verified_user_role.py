
import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider.settings')
django.setup()

from service_provider.models import VerifiedUser

def check_super_admin_role():
    try:
        # Search by phone number or hardcoded ID
        phone = "9876543210"
        user = VerifiedUser.objects.filter(phone_number=phone).first()
        
        if not user:
            print(f"❌ User with phone {phone} not found in VerifiedUser table.")
            # Try by email just in case
            email = "superadmin.manual@petleo.com"
            user = VerifiedUser.objects.filter(email=email).first()
            if not user:
                print(f"❌ User with email {email} also not found.")
                return

        print(f"✅ Found VerifiedUser: {user.email} (ID: {user.auth_user_id})")
        print(f"   - Role: '{user.role}'")
        print(f"   - Phone: {user.phone_number}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_super_admin_role()
