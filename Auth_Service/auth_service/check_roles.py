import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import Role

print("--- ROLES ---")
for r in Role.objects.all():
    print(f"ID: {r.id} | Name: {r.name}")
