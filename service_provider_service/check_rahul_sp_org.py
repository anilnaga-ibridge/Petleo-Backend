import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee
rahul_auth_id = '5c3b54b9-aa99-441d-8598-df3aea0b59fd'

emps = OrganizationEmployee.objects.filter(auth_user_id=rahul_auth_id)
print("--- Service Provider Employees ---")
for e in emps:
    print(f"Employee ID: {e.id}")
    print(f"Auth ID: {e.auth_user_id}")
    print(f"Organization ID (Provider): {e.organization_id}")
    print(f"Organization Name: {e.organization.verified_user.full_name if e.organization and e.organization.verified_user else 'No Org'}")
    if e.organization and e.organization.verified_user:
        print(f"Org Auth ID: {e.organization.verified_user.auth_user_id}")
        
