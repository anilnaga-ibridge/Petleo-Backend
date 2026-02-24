import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderCapabilityAccess
from service_provider.models import VerifiedUser

# Get the user (raj@gmail.com)
user = VerifiedUser.objects.filter(email="raj@gmail.com").first()
if not user:
    print("User not found")
    exit()

print(f"User: {user.full_name} ({user.email})")
print("\n=== ProviderCapabilityAccess Records ===")

caps = ProviderCapabilityAccess.objects.filter(user=user).order_by('service_id', 'category_id', 'facility_id')

for cap in caps:
    print(f"\nService: {cap.service_id}")
    print(f"  Category: {cap.category_id}")
    print(f"  Facility: {cap.facility_id}")
    print(f"  Pricing: {cap.pricing_id}")
    print(f"  Permissions: view={cap.can_view}, create={cap.can_create}, edit={cap.can_edit}, delete={cap.can_delete}")

print("\n=== Testing _build_permission_tree ===")
from service_provider.utils import _build_permission_tree
menu = _build_permission_tree(user)

import json
print(json.dumps(menu, indent=2, default=str))
