
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser

try:
    users = VerifiedUser.objects.filter(full_name__icontains="Dhatha")
    for user in users:
        print(f"ID: {user.auth_user_id} | Name: {user.full_name} | Email: {user.email} | Avatar: {user.avatar_url}")
except Exception as e:
    print(f"Error: {e}")
