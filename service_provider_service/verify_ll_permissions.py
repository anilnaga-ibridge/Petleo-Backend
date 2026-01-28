
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

# Find ll@gmail.com
user = VerifiedUser.objects.filter(auth_user_id="076875b0-ca6b-4d96-a5a5-36f29e8cd976").first()
if not user:
    print("User ll@gmail.com not found.")
    sys.exit(1)

print(f"Checking permissions for: {user.full_name} ({user.email})")
tree = _build_permission_tree(user)

print(f"Tree size: {len(tree)} services")
found_vitals = False
for service in tree:
    print(f"Service: {service.get('service_key')} / {service.get('name')}")
    for cat in service.get('categories', []):
        cat_key = cat.get('category_key')
        print(f"  - Category: {cat.get('name')} (Key: {cat_key})")
        
        if cat_key == "VETERINARY_VITALS":
            found_vitals = True

if found_vitals:
    print("\n✅ SUCCESS: Found category with key VETERINARY_VITALS")
else:
    print("\n❌ FAILURE: VETERINARY_VITALS key missing for this user!")
