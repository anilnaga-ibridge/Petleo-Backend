import os
import django
import sys

# Setup Django
PROJECT_ROOT = "/Users/PraveenWorks/Anil Works/Petleo-Backend"
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "service_provider_service"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory, ProviderCapabilityAccess

# Target User: anil.naga@ibridge.digital
user_id = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec"
user = VerifiedUser.objects.filter(auth_user_id=user_id).first()

if not user:
    print(f"User {user_id} not found.")
    sys.exit(1)

print(f"Granting System access to {user.email}...")

import uuid

# 1. Ensure the System Management Service Template exists locally
# We use a static UUID for the super_admin_service_id to keep it consistent
SYSTEM_ADMIN_ID = "550e8400-e29b-41d4-a716-446655440000"
svc, _ = ProviderTemplateService.objects.get_or_create(
    super_admin_service_id=SYSTEM_ADMIN_ID,
    defaults={
        "name": "SYSTEM_ADMIN",
        "display_name": "System Management",
        "icon": "tabler-settings"
    }
)

# 2. Grant Service Level Permission
ProviderCapabilityAccess.objects.get_or_create(
    user=user,
    service_id=svc.super_admin_service_id,
    category_id=None,
    defaults={"can_view":True, "can_create":True, "can_edit":True, "can_delete":True}
)

# 3. Define and Grant System Categories
system_categories = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "Employee Management",
        "linked_capability": "EMPLOYEE_MANAGEMENT",
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "name": "Role Management",
        "linked_capability": "ROLE_MANAGEMENT",
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "name": "Customer Booking Management",
        "linked_capability": "CUSTOMER_BOOKING",
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440004",
        "name": "Clinic Management",
        "linked_capability": "CLINIC_MANAGEMENT",
    }
]

for cat_data in system_categories:
    # Ensure category template exists locally
    c_tmpl, _ = ProviderTemplateCategory.objects.get_or_create(
        super_admin_category_id=cat_data["id"],
        defaults={
            "service": svc,
            "name": cat_data["name"],
            "linked_capability": cat_data["linked_capability"]
        }
    )
    
    # Grant permission
    obj, created = ProviderCapabilityAccess.objects.get_or_create(
        user=user,
        service_id=svc.super_admin_service_id,
        category_id=c_tmpl.super_admin_category_id,
        defaults={
            "can_view": True,
            "can_create": True,
            "can_edit": True,
            "can_delete": True
        }
    )
    status = "Created" if created else "Exists"
    print(f"  - Category '{c_tmpl.name}' (Cap: {c_tmpl.linked_capability}): {status}")

print("\n✅ System Management Access Granted.")
