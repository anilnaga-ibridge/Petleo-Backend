
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

print("--- Auth Service User Roles ---")
users = User.objects.filter(email__in=["doctor@gmail.com", "receptionist2@gmail.com", "receptionist@gmail.com", "eswar@gmail.com"])
for user in users:
    print(f"Name: {user.full_name} | Role: {user.role.name if user.role else 'None'} | Email: {user.email}")
