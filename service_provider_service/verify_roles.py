import os
import django
import uuid

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, ProviderRole, ProviderRoleCapability, OrganizationEmployee

def test_permission_resolution():
    print("--- Testing Permission Resolution ---")
    
    # 1. Create a Provider User
    provider_user, _ = VerifiedUser.objects.get_or_create(
        auth_user_id=uuid.uuid4(),
        defaults={
            "full_name": "Test Clinic",
            "email": "clinic@test.com",
            "role": "organization",
            "permissions": ["VETERINARY_VISITS", "VETERINARY_VITALS", "VETERINARY_LABS"]
        }
    )
    
    provider_profile, _ = ServiceProvider.objects.get_or_create(verified_user=provider_user)
    
    # 2. Create a Role
    nurse_role, _ = ProviderRole.objects.get_or_create(
        provider=provider_profile,
        name="Senior Nurse"
    )
    
    ProviderRoleCapability.objects.get_or_create(provider_role=nurse_role, capability_key="VETERINARY_VITALS")
    ProviderRoleCapability.objects.get_or_create(provider_role=nurse_role, capability_key="VETERINARY_LABS")
    ProviderRoleCapability.objects.get_or_create(provider_role=nurse_role, capability_key="VETERINARY_PRESCRIPTIONS") # Not in plan
    
    # 3. Create an Employee
    employee = OrganizationEmployee.objects.create(
        auth_user_id=uuid.uuid4(),
        organization=provider_profile,
        provider_role=nurse_role,
        full_name="Nurse Joy",
        created_by=provider_user.auth_user_id
    )
    
    # 4. Resolve Permissions
    final_perms = employee.get_final_permissions()
    print(f"Plan Perms: {provider_user.permissions}")
    print(f"Role Perms: {list(nurse_role.capabilities.values_list('capability_key', flat=True))}")
    print(f"Final Perms (Expected: VITALS, LABS): {final_perms}")
    
    # 5. Test Overrides
    employee.permissions_json = {"ADD": ["VETERINARY_PRESCRIPTIONS"], "REMOVE": ["VETERINARY_LABS"]}
    employee.save()
    
    final_perms_overridden = employee.get_final_permissions()
    print(f"Final Perms with Overrides (Expected: VITALS, PRESCRIPTIONS): {final_perms_overridden}")

if __name__ == "__main__":
    test_permission_resolution()
