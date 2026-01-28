
import os
import django
import sys
import uuid

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

# 2. Find Service Template
svc = ProviderTemplateService.objects.filter(name__in=["VETERINARY_CORE", "VETERINARY"]).first()
if not svc:
    print("Service Template VETERINARY_CORE not found.")
    sys.exit(1)

print(f"Service: {svc.name} ({svc.super_admin_service_id})")

# 3. Find Category Template (Nurse Station)
cat = ProviderTemplateCategory.objects.filter(service=svc, name="Nurse Station").first()
if not cat:
    print("Category Nurse Station not found. Trying VETERINARY_VITALS...")
    cat = ProviderTemplateCategory.objects.filter(service=svc, linked_capability="VETERINARY_VITALS").first()

if not cat:
    print("Category not found at all.")
    sys.exit(1)

print(f"Category: {cat.name} ({cat.super_admin_category_id})")

# 4. Create/Update Permission
# Check logic: we need records for Service AND Category?
# Usually yes.
# A. Service Level
obj, created = ProviderCapabilityAccess.objects.get_or_create(
    user=user,
    service_id=svc.super_admin_service_id,
    category_id=None,
    defaults={
        "can_view": True,
        "can_create": True,
        "can_edit": True,
        "can_delete": True
    }
)
print(f"Service Permission: {'Created' if created else 'Exists'}")

# B. Category Level
obj, created = ProviderCapabilityAccess.objects.get_or_create(
    user=user,
    service_id=svc.super_admin_service_id,
    category_id=cat.super_admin_category_id,
    defaults={
        "can_view": True,
        "can_create": True,
        "can_edit": True,
        "can_delete": True
    }
)
print(f"Category Permission: {'Created' if created else 'Exists'}")
