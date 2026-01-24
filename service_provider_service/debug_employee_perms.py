import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole, ServiceProvider
from provider_dynamic_fields.models import ProviderCapabilityAccess
from service_provider.utils import _build_permission_tree
import json

def debug_role_perms():
    print("--- Searching for 'AllRounder' Role ---")
    roles = ProviderRole.objects.filter(name__icontains="AllRounder")
    
    if not roles.exists():
        print("❌ No role found with name matching 'AllRounder'. listing all roles:")
        for r in ProviderRole.objects.all():
            print(f" - {r.name} (ID: {r.id})")
        return

    for role in roles:
        print(f"\nRole Found: {role.name} (ID: {role.id})")
        print(f"Description: {role.description}")
        print(f"Capabilities Count: {role.capabilities.count()}")
        
        caps = list(role.capabilities.values('capability_key'))
        print(f"Role Capabilities: {json.dumps(caps, indent=2)}")
        
        # Find employees with this role
        employees = OrganizationEmployee.objects.filter(provider_role=role)
        print(f"Employees assigned: {employees.count()}")
        
        for emp in employees:
            print(f"\n  Checking Employee: {emp.full_name} ({emp.email})")
            user = emp.organization.verified_user # This is the ORG owner
            # We need the EMPLOYEE'S verified user to check their specific permissions
            from service_provider.models import VerifiedUser
            try:
                emp_user = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
                print(f"  VerifiedUser ID: {emp_user.auth_user_id}")
                
                # Check DB capabilities
                db_caps = ProviderCapabilityAccess.objects.filter(user=emp_user)
                print(f"  DB CapabilityAccess Count: {db_caps.count()}")
                for c in db_caps:
                     print(f"    - Service: {c.service_id}, Category: {c.category_id}, Facility: {c.facility_id} (View: {c.can_view})")

                # Run logic
                tree = _build_permission_tree(emp_user)
                print(f"  Calculated Permission Tree Keys:")
                for s in tree:
                    print(f"    - Service: {s.get('service_name')} ({s.get('service_key')}) [View: {s.get('can_view')}]")
                    for c in s.get('categories', []):
                         print(f"      - Category: {c.get('category_name')} [View: {c.get('can_view')}]")
                
            except VerifiedUser.DoesNotExist:
                print("  ❌ VerifiedUser not found for employee")

if __name__ == "__main__":
    debug_role_perms()
