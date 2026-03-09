import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee

emps = OrganizationEmployee.objects.filter(email='praveen@gmail.com')
for emp in emps:
    print(f"\n--- Employee: {emp.full_name} ({emp.email}) ---")
    print(f"Role Name: {emp.provider_role.name if emp.provider_role else 'None'}")
    
    org_caps = emp.organization.verified_user.get_all_plan_capabilities()
    print(f"Org Caps: {org_caps}")
    
    if emp.provider_role:
        role_caps = set(emp.provider_role.capabilities.values_list("capability_key", flat=True))
    else:
        legacy_key = (emp.role or "employee").lower()
        role_caps = set(emp.LEGACY_ROLE_MAP.get(legacy_key, []))
        
    print(f"Role Caps: {role_caps}")
    
    final = org_caps.intersection(role_caps)
    print(f"Intersection: {final}")
    print(f"Final Permissions (from method): {emp.get_final_permissions()}")
