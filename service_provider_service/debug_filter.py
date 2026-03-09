import os
import django
import json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee
from service_provider.utils import _build_permission_tree

emp = OrganizationEmployee.objects.get(email='praveen@gmail.com')
subscription_owner = emp.organization.verified_user

permissions_list = _build_permission_tree(subscription_owner, request=None)
user_caps = set(emp.get_final_permissions())

print(f"User Caps: {sorted(user_caps)}")
print(f"\nTree before filter:")
for svc in permissions_list:
    print(f"  - {svc['service_key']} ({svc['service_name']}): can_view={svc['can_view']}")
    for cat in svc.get('categories', []):
        print(f"      cat: {cat.get('category_key')} can_view={cat.get('can_view')}")

# Simulate exactly what views.py does now
SERVICE_KEY_ALIASES = {
    "VETERINARY": "VETERINARY_CORE",
}

filtered_permissions = []
for service in permissions_list:
    service_key = service.get('service_key')
    resolved_key = SERVICE_KEY_ALIASES.get(service_key, service_key)
    has_service_access = (service_key in user_caps) or (resolved_key in user_caps)
    
    filtered_categories = []
    for category in service.get('categories', []):
        cat_key = category.get('linked_capability') or category.get('category_key')
        if cat_key and cat_key in user_caps:
            rebuilt_category = category.copy()
            rebuilt_category['can_view'] = True
            rebuilt_category['can_create'] = True
            rebuilt_category['can_edit'] = True
            rebuilt_category['can_delete'] = False
            filtered_categories.append(rebuilt_category)
    
    if has_service_access or filtered_categories:
        filtered_service = service.copy()
        filtered_service['categories'] = filtered_categories
        if service_key != resolved_key:
            filtered_service['service_key'] = resolved_key
        filtered_permissions.append(filtered_service)

print(f"\nFiltered result (sent to frontend):")
print(json.dumps(filtered_permissions, indent=2, default=str))
