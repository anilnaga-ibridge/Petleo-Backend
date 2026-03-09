"""
Backfill script: Fix StaffClinicAssignment records that have generic 'employee' role
                 and/or empty permissions by looking up the actual provider role
                 from the Provider Service (port 8002).
"""
import os
import sys
import django
import requests

sys.path.insert(0, '/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment
from veterinary.services import RolePermissionService

PROVIDER_SERVICE_URL = "http://127.0.0.1:8002"

def get_employee_role_from_provider(auth_user_id):
    """
    Calls the Provider Service to get the employee's actual ProviderRole name.
    """
    try:
        # First try to look up via the employees list
        # We need an auth token - let's just check the DB directly via Provider Service Django
        # Import provider service models is not possible cross-service. Use the debug endpoint instead.
        import subprocess
        result = subprocess.run([
            '/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service/venv/bin/python',
            '-c',
            f"""
import os, django, sys
sys.path.insert(0, '/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()
from service_provider.models import OrganizationEmployee
emp = OrganizationEmployee.objects.filter(auth_user_id='{auth_user_id}').first()
if emp and emp.provider_role:
    print(emp.provider_role.name)
else:
    print('N/A')
"""
        ], capture_output=True, text=True, timeout=5)
        role_name = result.stdout.strip()
        if role_name and role_name != 'N/A':
            return role_name
    except Exception as e:
        print(f"  Error fetching role for {auth_user_id}: {e}")
    return None


print("--- Backfilling StaffClinicAssignments ---\n")

assignments = StaffClinicAssignment.objects.filter(is_active=True)

for a in assignments:
    needs_update = False
    role = a.role or (a.staff.role if a.staff else None) or 'employee'
    
    print(f"👤 Staff: {a.staff.full_name if a.staff.full_name else a.staff.auth_user_id}")
    print(f"   Clinic: {a.clinic.name}")
    print(f"   Current Role: {role}")
    print(f"   Current Perms: {a.permissions}")
    
    # Case 1: Role is generic 'employee', look up real role
    if role.lower() == 'employee':
        real_role = get_employee_role_from_provider(a.staff.auth_user_id)
        if real_role:
            print(f"   ✅ Found real role: {real_role}")
            a.role = real_role
            role = real_role
            needs_update = True
        else:
            print(f"   ⚠️  Could not find real role. Keeping 'employee'.")
    
    # Case 2: No permissions (or empty) — fill from role
    if not a.permissions:
        resolved_perms = RolePermissionService.get_permissions_for_role(role)
        if resolved_perms:
            print(f"   ✅ Setting permissions from role '{role}': {resolved_perms}")
            a.permissions = resolved_perms
            needs_update = True
    
    if needs_update:
        a.save()
        print(f"   ✅ SAVED\n")
    else:
        print(f"   — No update needed\n")

print("--- Backfill complete ---")
