import os
import django
import sys

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderCapabilityAccess
from service_provider.models import VerifiedUser

auth_id = '45c80593-73d9-4eb1-b479-84c791a4ea40'
user = VerifiedUser.objects.filter(auth_user_id=auth_id).first()

if not user:
    print(f"User {auth_id} not found")
    # List all users to see if IDs are different
    print("All users in DB:")
    for u in VerifiedUser.objects.all():
        print(f" - {u.full_name} ({u.auth_user_id})")
    sys.exit(1)

print(f"Found User: {user.full_name} | ID: {user.id} | AuthID: {user.auth_user_id}")

perms = ProviderCapabilityAccess.objects.filter(user=user)
print(f"Total Perms for {user.full_name}: {perms.count()}")

if perms.count() == 0:
    # Maybe perms are linked by auth_id directly? (Unlikely but let's check)
    print("Checking if linked by direct ID match...")
    all_perms = ProviderCapabilityAccess.objects.all()
    print(f"Total Perms in entire DB: {all_perms.count()}")

print("\n--- First 30 Permissions ---")
for p in perms[:30]:
    svc = p.service_id
    cat = p.category_id
    fac = p.facility_id
    price = p.pricing_id
    print(f"Svc: {svc} | Cat: {cat} | Fac: {fac} | Price: {price}")
