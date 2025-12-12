import os
import django
import sys

# Setup Django environment for Auth Service
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

user_id = "72957f4c-076a-4c52-8947-626ffa9b5477"

print(f"Checking Auth Service for User ID: {user_id}")
print("-" * 40)

try:
    user = User.objects.get(id=user_id)
    print(f"✅ User FOUND in Auth Service: {user.email} (Role: {user.role})")
except User.DoesNotExist:
    print("❌ User NOT FOUND in Auth Service")
except Exception as e:
    print(f"❌ Error checking Auth Service: {e}")
