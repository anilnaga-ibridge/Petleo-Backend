
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
try:
    user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
    print(f"User Found: {user.full_name}")
    print(f"Email: {user.email}")
    print(f"Avatar URL: {user.avatar_url}")
except VerifiedUser.DoesNotExist:
    print("User not found in VerifiedUser table.")
except Exception as e:
    print(f"Error: {e}")
