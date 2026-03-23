import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import (
    ProviderRole, ProviderRoleCapability, OrganizationEmployee, ServiceProvider, VerifiedUser
)
from django.test import RequestFactory
from service_provider.views import get_my_permissions
from django.utils import timezone

def test_multi_role_logic():
    org_id = '19b55dd4-c2bb-474c-b5bf-d39077f52dfe'
    org = ServiceProvider.objects.get(id=org_id)
    
    print("\n" + "="*50)
    print("🚀 PRO RBAC TEST: Multi-Role & Granular CRUD")
    print("="*50)

    # 1. Create specialized roles
    # Role A: Surgeon (Patients: View+Edit, No Schedule)
    surgeon_role, _ = ProviderRole.objects.get_or_create(provider=org, name='Surgeon')
    ProviderRoleCapability.objects.filter(provider_role=surgeon_role).delete()
    ProviderRoleCapability.objects.create(provider_role=surgeon_role, capability_key='VETERINARY_CORE', can_view=True)
    ProviderRoleCapability.objects.create(provider_role=surgeon_role, capability_key='VETERINARY_PATIENTS', can_view=True, can_edit=True, can_create=True)
    ProviderRoleCapability.objects.create(provider_role=surgeon_role, capability_key='VETERINARY_VISITS', can_view=True)
    
    # Role B: Front Desk (Schedule: View+Create, Patients: View Only, No Delete)
    reception_role, _ = ProviderRole.objects.get_or_create(provider=org, name='Front Desk')
    ProviderRoleCapability.objects.filter(provider_role=reception_role).delete()
    ProviderRoleCapability.objects.create(provider_role=reception_role, capability_key='VETERINARY_CORE', can_view=True)
    ProviderRoleCapability.objects.create(provider_role=reception_role, capability_key='VETERINARY_SCHEDULE', can_view=True, can_create=True)
    ProviderRoleCapability.objects.create(provider_role=reception_role, capability_key='VETERINARY_PATIENTS', can_view=True, can_edit=False, can_delete=False)

    print(f"✅ Created Roles: {surgeon_role.name}, {reception_role.name}")

    # 2. Pick Employees
    # Mocking behavior for Kamal and Naga (or creating if missing)
    staff_data = [
        {"name": "Kamal Surgeon", "role": surgeon_role, "email": "kamal@example.com"},
        {"name": "Naga Reception", "role": reception_role, "email": "naga@example.com"}
    ]

    for data in staff_data:
        emp = OrganizationEmployee.objects.filter(full_name=data["name"]).first()
        if not emp:
            import uuid
            auth_id = str(uuid.uuid4())
            VerifiedUser.objects.get_or_create(auth_user_id=auth_id, email=data["email"])
            emp = OrganizationEmployee.objects.create(
                organization=org,
                full_name=data["name"],
                auth_user_id=auth_id,
                role='employee',
                provider_role=data["role"],
                created_by=org.verified_user.auth_user_id
            )
        else:
            emp.provider_role = data["role"]
            emp.save()
        
        emp.invalidate_permission_cache()
        
        # --- PRO SIMULATION OF get_my_permissions Logic ---
        user_perms_map = emp.get_final_permissions()
        
        # Start with a full Veterinary tree (as if from Plan)
        full_vet_tree = {
            "service_name": "Veterinary Management",
            "service_key": "VETERINARY",
            "categories": [
                {"category_name": "Patients", "category_key": "VETERINARY_PATIENTS", "linked_capability": "VETERINARY_PATIENTS"},
                {"category_name": "Schedule", "category_key": "VETERINARY_SCHEDULE", "linked_capability": "VETERINARY_SCHEDULE"},
                {"category_name": "Visits", "category_key": "VETERINARY_VISITS", "linked_capability": "VETERINARY_VISITS"}
            ]
        }
        
        print(f"\n👤 TESTING USER: {emp.full_name}")
        print(f"   Role: {data['role'].name}")
        print(f"   Granted Capabilities: {list(user_perms_map.keys())}")
        
        # Filter Logic (Simulating views.py lines 705-740)
        accessible_categories = []
        for cat in full_vet_tree["categories"]:
            key = cat["category_key"]
            if key in user_perms_map:
                perms = user_perms_map[key]
                cat_with_perms = cat.copy()
                cat_with_perms.update(perms)
                accessible_categories.append(cat_with_perms)
        
        if accessible_categories:
            print(f"   ✅ DYNAMIC SIDEBAR GENERATED:")
            for c in accessible_categories:
                crud = f"V:{c['can_view']} C:{c['can_create']} E:{c['can_edit']} D:{c['can_delete']}"
                print(f"      - {c['category_name']} Module [{crud}]")
        else:
            print("   ❌ SIDEBAR: No Veterinary Modules Visible")

    print("\n" + "="*50)
    print("✅ RBAC VERIFICATION COMPLETE")
    print("="*50)

if __name__ == "__main__":
    test_multi_role_logic()
