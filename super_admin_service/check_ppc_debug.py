import os
import django
import sys

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import ProviderPlanCapability
from django.contrib.auth import get_user_model
from dynamic_services.models import Service

User = get_user_model()
auth_id = '45c80593-73d9-4eb1-b479-84c791a4ea40'
user = User.objects.filter(id=auth_id).first()

if not user:
    print(f"User {auth_id} not found in Super Admin")
    sys.exit(1)

perms = ProviderPlanCapability.objects.filter(user=user)
print(f"Total ProviderPlanCapability for {user.full_name}: {perms.count()}")

# Group by service name
services = {}
for p in perms:
    s_name = p.service.name if p.service else "None"
    s_id = str(p.service.id) if p.service else "None"
    if s_name not in services:
        services[s_name] = set()
    services[s_name].add(s_id)

print("\n--- Services in Permissions ---")
for s_name, ids in services.items():
    print(f"Service: {s_name} | IDs: {list(ids)}")

print("\n--- All Grooming Services in DB ---")
all_grooming = Service.objects.filter(name__icontains='Grooming')
for s in all_grooming:
    print(f" - {s.name} ({s.id})")

