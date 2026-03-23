
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole, ProviderRoleCapability

def verify_receptionist():
    print("=== RECEPTIONIST ROLE VERIFICATION REPORT ===\n")
    
    # 1. Check for the Role
    roles = ProviderRole.objects.filter(name__iexact="Receptionist")
    
    if not roles.exists():
        print("❌ No 'Receptionist' role found in the system.")
        return

    for role in roles:
        print(f"Role: {role.name} (ID: {role.id})")
        print(f"Organization: {role.organization}")
        print(f"Description: {role.description or 'No description'}")
        
        # 2. Check Capabilities and CRUD
        caps = ProviderRoleCapability.objects.filter(provider_role=role)
        print(f"\n--- Related Capabilities & CRUD Permissions ({caps.count()}) ---")
        if caps.exists():
            for cap in caps:
                crud = []
                if cap.can_view: crud.append("VIEW")
                if cap.can_create: crud.append("CREATE")
                if cap.can_edit: crud.append("EDIT")
                if cap.can_delete: crud.append("DELETE")
                
                # Handling both name and key for clarity
                cap_name = cap.capability.name if hasattr(cap.capability, 'name') else 'Unknown'
                cap_key = cap.capability_key
                print(f"✅ {cap_name} ({cap_key}) -> [{', '.join(crud) if crud else 'NONE'}]")
        else:
            print("⚠️ Warning: No capabilities linked to this role yet.")

        # 3. Check Assigned Employees
        employees = OrganizationEmployee.objects.filter(provider_role=role)
        print(f"\n--- Assigned Employees ({employees.count()}) ---")
        if employees.exists():
            for emp in employees:
                print(f"👤 {emp.full_name} ({emp.email})")
                print(f"   - Internal System Role (Type): {emp.role}")
                print(f"   - Provider Instance: {emp.organization}")
                print(f"   - Status: {emp.status}")
        else:
            print("ℹ️ No employees currently assigned to this role.")
            
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    verify_receptionist()
