
import os, sys, django, json
sys.path.insert(0, '/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()
from service_provider.models import OrganizationEmployee, VerifiedUser
from service_provider.utils import _build_permission_tree

# 1. Get employee and their organization owner
emp = OrganizationEmployee.objects.get(auth_user_id='66e9b147-e9bc-432c-b78b-b513a9b22901')
org_owner = emp.organization.verified_user

# 2. Build the BASE tree (from Org Plan)
permissions_list = _build_permission_tree(org_owner)

# 3. Apply Employee Filtering (Mirroring get_my_permissions in views.py)
user_caps = set(emp.get_final_permissions())
SERVICE_KEY_ALIASES = {"VETERINARY": "VETERINARY_CORE"}

filtered_permissions = []
for service in permissions_list:
    service_key = service.get('service_key')
    resolved_key = SERVICE_KEY_ALIASES.get(service_key, service_key)
    has_service_access = (service_key in user_caps) or (resolved_key in user_caps)
    
    filtered_categories = []
    
    cats = service.get('categories', [])
    if isinstance(cats, dict):
        cats = list(cats.values())
        
    for category in cats:
        cat_key = category.get('linked_capability') or category.get('category_key')
        if cat_key and cat_key in user_caps:
            rebuilt_category = category.copy()
            rebuilt_category['can_view'] = True
            filtered_categories.append(rebuilt_category)
    
    if has_service_access or filtered_categories:
        filtered_service = service.copy()
        filtered_service['categories'] = filtered_categories
        if service_key != resolved_key:
            filtered_service['service_key'] = resolved_key
        filtered_permissions.append(filtered_service)

# 4. Result
vet_service = next((p for p in filtered_permissions if p['service_key'] == 'VETERINARY_CORE'), None)
if vet_service:
    print('VETERINARY_CORE CATEGORIES:')
    for cat in vet_service['categories']:
        print(f" - Name: {cat.get('name')} | Key: {cat.get('category_key')} | Linked: {cat.get('linked_capability')}")
else:
    print('ERROR: VETERINARY_CORE not found in final perms')
