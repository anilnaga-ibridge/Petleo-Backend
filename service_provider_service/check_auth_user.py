import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

def check_auth_user():
    auth_id = "7470623a-ee4b-4922-99f5-3ce2f17171d7"
    print(f"--- Checking VerifiedUser for Auth ID: {auth_id} ---")
    
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_id)
        print(f"✅ Found User: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Is Active: {user.is_active}")
    except VerifiedUser.DoesNotExist:
        print("❌ User NOT FOUND in VerifiedUser table.")
        print("   This confirms the Kafka event was missed or failed.")

if __name__ == "__main__":
    check_auth_user()
