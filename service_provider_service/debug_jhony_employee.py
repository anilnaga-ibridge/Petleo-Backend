import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from org_employees.models import OrganizationEmployee

print("Checking employee for jhony...")
# Get the employee for jhony
uuid_str = '938c07c7-271c-4db7-adba-da11ac5999bd'
try:
    oe = OrganizationEmployee.objects.get(verified_user_id=uuid_str)
    print(f"Employee found via get()! ID: {oe.id}")
except Exception as e:
    print(f"Error getting oe: {e}")
    oe = None
    for emp in OrganizationEmployee.objects.all():
        if str(emp.verified_user_id) == uuid_str:
            oe = emp
            break

if oe:
    print(f"Employee found! ID: {oe.id}")
    print(f"Role: {oe.role.name if oe.role else 'None'}")
    if oe.role:
        print(f"Role Caps: {oe.role.capabilities}")
    print(f"Direct Perms: {oe.permissions}")
    print(f"Final Perms (from method): {oe.get_final_permissions()}")
else:
    print("Could not find employee record.")
