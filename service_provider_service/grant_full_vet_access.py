
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

# 2. Find ALL VETERINARY_CORE Templates
svcs = ProviderTemplateService.objects.filter(name="VETERINARY_CORE")
if not svcs.exists():
    print("VETERINARY_CORE service templates not found.")
    sys.exit(1)

print(f"Found {svcs.count()} VETERINARY_CORE templates. Processing all...")

for svc in svcs:
    print(f"\nProcessing Service: {svc.name} (ID: {svc.super_admin_service_id})")

    # 3. Grant Service Level Permission (in case missing)
    ProviderCapabilityAccess.objects.get_or_create(
        user=user,
        service_id=svc.super_admin_service_id,
        category_id=None,
        defaults={"can_view":True, "can_create":True, "can_edit":True, "can_delete":True}
    )

    # 4. Grant All Categories
    cats = ProviderTemplateCategory.objects.filter(service=svc)
    print(f"Found {cats.count()} categories.")

    for c in cats:
        obj, created = ProviderCapabilityAccess.objects.get_or_create(
            user=user,
            service_id=svc.super_admin_service_id,
            category_id=c.super_admin_category_id,
            defaults={
                "can_view": True,
                "can_create": True,
                "can_edit": True,
                "can_delete": True
            }
        )
        status = "Created" if created else "Exists"
        print(f"  - Category '{c.name}' (Cap: {c.linked_capability}): {status}")

print("\n✅ Full Veterinary Access Granted for ALL templates.")
