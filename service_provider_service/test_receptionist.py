import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole
from django.core.cache import cache

# Find any employee who has 'receptionist' in their custom provider_role or legacy role
emps = OrganizationEmployee.objects.all()
receptionist = None
for emp in emps:
    if emp.provider_role and 'reception' in emp.provider_role.name.lower():
        receptionist = emp
        break
    elif emp.role and 'reception' in emp.role.lower():
        receptionist = emp
        break

if not receptionist:
    print("Could not find any Receptionist employee to test.")
else:
    print(f"Testing Employee: {receptionist.full_name} | Role: {receptionist.role} | ProviderRole: {receptionist.provider_role}")
    
    # Check what capabilities they have
    perms = receptionist.get_final_permissions()
    print(f"Final Permissions List: {perms}")
    
    if receptionist.provider_role:
        role_caps = list(receptionist.provider_role.capabilities.values_list('capability_key', flat=True))
        print(f"Role's Raw Capabilities: {role_caps}")
        
    org_caps = receptionist.organization.verified_user.get_all_plan_capabilities()
    print(f"Org's Raw Capabilities: {org_caps}")
