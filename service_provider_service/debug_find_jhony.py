import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, ProviderRole
from org_employees.models import OrganizationEmployee
from django.apps import apps

u = VerifiedUser.objects.filter(email__icontains='jhony').first()
if not u:
    print("User 'jhony' not found in VerifiedUser")
    exit()

print(f"VerifiedUser: {u.auth_user_id} - {u.email} - {u.full_name}")

auth_id = str(u.auth_user_id)

sp = ServiceProvider.objects.filter(verified_user=u).first()
print(f"ServiceProvider: {sp}")

oe = OrganizationEmployee.objects.filter(verified_user_id=auth_id).first()
if getattr(oe, 'verified_user', None) is None and getattr(oe, 'auth_user_id', None) is not None:
    # It might be using auth_user_id directly
    oe = OrganizationEmployee.objects.filter(auth_user_id=auth_id).first()
    
print(f"OrganizationEmployee: {oe}")
if oe:
    print(f" - Role: {oe.role.name if oe.role else 'None'}")
    if oe.role:
        print(f" - Capabilities: {oe.role.capabilities}")
    print(f" - Direct Perms: {oe.permissions}")

# Just search the entire DB for the auth user id
print(f"\nSearching all models for UUID: {auth_id}")
for model in apps.get_models():
    try:
        # Check if model has a UUIDField or ForeignKey
        for field in model._meta.get_fields():
            if hasattr(field, 'name') and field.name in ['verified_user', 'provider', 'employee', 'user']:
                qs = model.objects.filter(**{field.name: auth_id})
                if qs.exists():
                    print(f"Found in {model.__name__}.{field.name}: {qs.count()} records")
            elif hasattr(field, 'name') and field.name in ['auth_user_id']:
                qs = model.objects.filter(**{field.name: auth_id})
                if qs.exists():
                    print(f"Found in {model.__name__}.{field.name}: {qs.count()} records")
    except Exception as e:
        pass
