
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory, ProviderCapabilityAccess

# 1. Find User
user = VerifiedUser.objects.filter(auth_user_id="076875b0-ca6b-4d96-a5a5-36f29e8cd976").first()
if not user:
    print("User ll@gmail.com not found.")
    sys.exit(1)

# List of Service Names to Restore
SERVICES_TO_RESTORE = ["DAY CARE", "TRAINNING", "VETERINARY_CORE"] 
# VETERINARY_CORE included to ensure full coverage beyond just Nurse Station

print(f"Restoring permissions for: {user.full_name} ({user.email})")

for svc_name in SERVICES_TO_RESTORE:
    # Find Service Template
    # We check both exact match and likely variants just in case
    svc = ProviderTemplateService.objects.filter(name__iexact=svc_name).first()
    if not svc:
        print(f"⚠️ Service Template '{svc_name}' not found. Skipping.")
        continue

    print(f"Processing Service: {svc.name}")

    # Grant Service Level Permission
    ProviderCapabilityAccess.objects.get_or_create(
        user=user,
        service_id=svc.super_admin_service_id,
        category_id=None,
        defaults={"can_view":True, "can_create":True, "can_edit":True, "can_delete":True}
    )

    # Grant All Categories under this Service
    cats = ProviderTemplateCategory.objects.filter(service=svc)
    if not cats.exists():
        print("  No categories found.")
    
    for c in cats:
        obj, created = ProviderCapabilityAccess.objects.get_or_create(
            user=user,
            service_id=svc.super_admin_service_id,
            category_id=c.super_admin_category_id,
            defaults={"can_view":True, "can_create":True, "can_edit":True, "can_delete":True}
        )
        status = "Created" if created else "Exists"
        print(f"  - Category {c.name}: {status}")

print("✅ Permissions restoration complete.")
