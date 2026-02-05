#!/usr/bin/env python
"""
Quick diagnostic: Check what's actually in the database for employee Kamal
"""
import os, sys, django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ProviderRole, ProviderRoleCapability, OrganizationEmployee

print("\n" + "="*100)
print(" KAMAL'S PERMISSION DIAGNOSTIC")
print("="*100 + "\n")

# Find Kamal
emp = OrganizationEmployee.objects.filter(email="kamal@gmail.com").first()
if not emp:
    print(" Employee 'kamal@gmail.com' not found")
    sys.exit(1)

print(f"Employee: {emp.full_name} ({emp.email})")
print(f"Auth User ID: {emp.auth_user_id}")
print(f"Status: {emp.status}")
print(f"Role String: {emp.role}")
print(f"Provider Role: {emp.provider_role}")

if emp.provider_role:
    role = emp.provider_role
    print(f"\n--- Provider Role Details ---")
    print(f"Role Name: {role.name}")
    print(f"Role Description: {role.description}")
    
    caps = role.capabilities.all()
    print(f"\nCapabilities ({caps.count()}):")
    for cap in caps:
        print(f"  - {cap.capability_key}")
    
    print(f"\n--- Organization Plan Capabilities ---")
    org_caps = emp.organization.verified_user.get_all_plan_capabilities()
    print(f"Count: {len(org_caps)}")
    print(f"List: {sorted(list(org_caps))}")
    
    # Calculate intersection
    role_caps = set(caps.values_list('capability_key', flat=True))
    intersection = org_caps.intersection(role_caps)
    
    print(f"\n--- INTERSECTION (Plan ∩ Role) ---")
    print(f"Count: {len(intersection)}")
    print(f"List: {sorted(list(intersection))}")
    
    print(f"\n--- FINAL PERMISSIONS ---")
    final_perms = emp.get_final_permissions()
    print(f"Count: {len(final_perms)}")
    print(f"List: {sorted(final_perms)}")
else:
    print("\n❌ NO PROVIDER ROLE ASSIGNED")

print(f"\n{'='*100}\n")
