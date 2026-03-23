import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Service_Provider.settings')
django.setup()

from service_provider.models import ProviderRole, ProviderCapabilityAccess, OrganizationEmployee

def check_receptionist_role():
    print("--- Searching for custom 'receptionist' roles ---")
    roles = ProviderRole.objects.filter(name__icontains='receptionist')
    if not roles.exists():
        print("No roles containing 'receptionist' found.")
        return

    for role in roles:
        print(f"\nRole ID: {role.id} | Name: '{role.name}' | Type: {role.get_role_type_display() if hasattr(role, 'get_role_type_display') else role.role_type} | Org ID: {role.organization_id}")
        
        print("  Capabilities & Permissions:")
        capabilities = ProviderCapabilityAccess.objects.filter(role=role)
        if not capabilities.exists():
            print("    - No capabilities assigned.")
        else:
            for cap in capabilities:
                print(f"    - Module: {cap.module_name}")
                print(f"      View: {cap.can_view}, Create: {cap.can_create}, Edit: {cap.can_edit}, Delete: {cap.can_delete}")

        print("\n  Assigned Employees:")
        employees = OrganizationEmployee.objects.filter(provider_role=role)
        if not employees.exists():
            print("    - No employees assigned to this role.")
        else:
            for emp in employees:
                print(f"    - Empl ID: {emp.id} | Name: {emp.full_name} | Email: {emp.email} | Status: {emp.status}")
                print(f"      Auth ID: {emp.auth_user_id} | Org: {emp.organization.name if emp.organization else 'N/A'}")

if __name__ == '__main__':
    check_receptionist_role()
