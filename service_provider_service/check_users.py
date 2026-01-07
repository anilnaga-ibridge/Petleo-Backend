
import os
import django
import sys

# Setup Django environment for Service Provider Service
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from django.contrib.auth import get_user_model

# Get the user ID from the token (we can simulate or check all users)
# Since we don't have the token here, let's list all VerifiedUsers to see if our Super Admin is there.
print("Checking VerifiedUser table in provider_db...")
users = VerifiedUser.objects.all()
for user in users:
    print(f"User: {user.email}, Auth ID: {user.auth_user_id}, Role: {getattr(user, 'role', 'N/A')}")

print("\nDone.")
