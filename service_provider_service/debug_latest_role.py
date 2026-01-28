import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ProviderRole, ProviderRoleCapability, VerifiedUser

print("--- Inspecting Latest Provider Roles ---")
roles = ProviderRole.objects.all().order_by('-created_at')[:3]

for role in roles:
    print(f"\n==========================================")
    print(f"Role: {role.name} (ID: {role.id})")
    print(f"Provider: {role.provider.verified_user.email}")
    
    # 1. Role Capabilities
    role_caps = set(
        ProviderRoleCapability.objects.filter(provider_role=role).values_list('capability_key', flat=True)
    )
    print(f"Role Capabilities ({len(role_caps)}): {sorted(list(role_caps))}")
    
    # 2. Provider Plan Capabilities
    provider_user = role.provider.verified_user
    plan_caps = provider_user.get_all_plan_capabilities()
    print(f"Provider Plan Caps ({len(plan_caps)}): {sorted(list(plan_caps))}")
    
    # 3. Intersection (What Employee Gets)
    final_permissions = plan_caps.intersection(role_caps)
    print(f"Intersection (Employee Access): {sorted(list(final_permissions))}")
    
    if "GROOMING" in role_caps and "GROOMING" not in plan_caps:
        print("\n[!] WARNING: Role has 'GROOMING' but Provider Plan DOES NOT. Employee will NOT get access.")
    
print("\n--- End of Report ---")
