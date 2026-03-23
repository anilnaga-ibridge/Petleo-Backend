import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole, ProviderRoleCapability
from django.core.cache import cache
import json

def assign_manohar():
    print("--- 1. Locating Receptionist Role ---")
    roles = ProviderRole.objects.filter(name__iexact='Receptionist')
    if not roles.exists():
        print("ERROR: Receptionist role not found in DB.")
        return
        
    role = roles.first()
    print(f"✅ Found Role: {role.name} (ID: {role.id})")
    
    caps = ProviderRoleCapability.objects.filter(provider_role=role)
    print(f"Capabilities tied to Role: {[c.capability.name if hasattr(c.capability, 'name') else c.capability_key for c in caps]}")
    
    print("\n--- 2. Updating Manohar ---")
    emps = OrganizationEmployee.objects.filter(full_name__icontains='Manohar')
    if not emps.exists():
        print("ERROR: Manohar not found.")
        return
        
    for emp in emps:
        print(f"Employee found: {emp.full_name} ({emp.auth_user_id})")
        emp.provider_role = role
        emp.save()
        emp.invalidate_permission_cache()
        print("✅ Manohar's provider_role updated to Receptionist.")
        
        perms = emp.get_final_permissions()
        print(f"\n✅ Newly calculated permissions for Manohar:")
        # print(json.dumps(perms, indent=2))
        for k, v in perms.items():
            print(f"  - {k}: {v}")

if __name__ == '__main__':
    assign_manohar()
