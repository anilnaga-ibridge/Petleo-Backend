import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User, Role

print("--- USERS WITH ROLE 'employee' ---")
try:
    role = Role.objects.get(name='employee')
    users = User.objects.filter(role=role)
    for u in users:
        print(f"User: {u.email} | Phone: {u.phone_number} | Role: {u.role.name}")
except Role.DoesNotExist:
    print("Role 'employee' not found.")
