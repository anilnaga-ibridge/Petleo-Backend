from service_provider.models import Capability, ProviderRole, ProviderRoleCapability
from django.db import transaction

def seed_capabilities():
    # 1. Define New Management Capabilities
    mgmt_caps = [
        ("MANAGE_SERVICES", "Manage Services", "Admin", "Can create and edit service details"),
        ("MANAGE_PRICING", "Manage Pricing", "Admin", "Can update service prices"),
        ("MANAGE_FACILITIES", "Manage Facilities", "Admin", "Can create and edit facilities"),
        ("VIEW_ANALYTICS", "View Analytics", "Admin", "Can view business performance reports"),
    ]

    # 2. Define Execution Skills (Ensure these exist)
    exec_caps = [
        ("GROOMING_EXEC", "Grooming Specialist", "Execution", "Can perform grooming services"),
        ("SPA_THERAPIST", "Spa Therapist", "Execution", "Can perform spa treatments"),
        ("TRAINER", "Pet Trainer", "Execution", "Can conduct training sessions"),
    ]

    print("--- Seeding Capabilities ---")
    for key, label, group, desc in mgmt_caps + exec_caps:
        cap, created = Capability.objects.get_or_create(key=key, defaults={
            "label": label, 
            "group": group,
            "description": desc
        })
        if created:
            print(f"✅ Created Capability: {key}")
        else:
            print(f"ℹ️  Capability exists: {key}")

def seed_roles():
    print("\n--- Seeding/Updating Roles ---")
    
    # 1. Manager Role (Has everything)
    manager_caps = [
        "VETERINARY_CORE", "MANAGE_SERVICES", "MANAGE_PRICING", "MANAGE_FACILITIES", 
        "VIEW_ANALYTICS", "VETERINARY_ADMIN_SETTINGS"
    ]
    
    # 2. Groomer Role (Execution Only)
    groomer_caps = ["VETERINARY_CORE", "GROOMING_EXEC"] # VETERINARY_CORE needed for basic dash access?
    
    # 3. Receptionist (Booking Management but not Service Config)
    reception_caps = ["VETERINARY_CORE", "VETERINARY_VISITS", "VETERINARY_SCHEDULE"]

    roles_config = {
        "Manager": manager_caps,
        "Groomer": groomer_caps,
        "Receptionist": reception_caps
    }

    # Note: ProviderRoles are provider-specific, so we can't seed them globally 
    # unless we iterate all providers or create System Roles (if supported).
    # For now, let's just ensure the Capabilities exist so the UI can use them.
    pass

if __name__ == '__main__':
    with transaction.atomic():
        seed_capabilities()
        # seed_roles() # Skip role seeding for now as it's provider-specific
