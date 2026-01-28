
import os
import django
import sys
import json

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from service_provider.utils import _build_permission_tree

# Find Naga Anil
user = VerifiedUser.objects.filter(full_name__icontains="Naga Anil").first()
if not user:
    print("User Naga Anil not found.")
    sys.exit(1)

print(f"Checking permissions for: {user.full_name}")
tree = _build_permission_tree(user)

found_vitals = False
for service in tree:
    print(f"Service: {service.get('service_key')} / {service.get('name')}")
    for cat in service.get('categories', []):
        cat_key = cat.get('category_key')
        linked = cat.get('linked_capability')
        print(f"  - Category: {cat.get('name')}")
        print(f"    Key: {cat_key} | Linked: {linked}")
        print(f"    Permissions: View={cat.get('can_view')}")
        
        if cat_key == "VETERINARY_VITALS":
            found_vitals = True

if found_vitals:
    print("\n✅ SUCCESS: Found category with key VETERINARY_VITALS")
else:
    print("\n❌ FAILURE: VETERINARY_VITALS key missing!")
