import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser
from provider_dynamic_fields.models import ProviderTemplateCategory
from service_provider.utils import _build_permission_tree
from django.core.cache import cache

def verify_employees():
    employee_names = ['Praveen', 'Veterinary Nurse', 'Rahul', 'Kamal']
    
    for name in employee_names:
        try:
            print(f"\n{'='*50}")
            print(f"🕵️  DEBUGGING PERMISSIONS FOR: {name}")
            print(f"{'='*50}")
            
            # Get Employee Record
            emp = OrganizationEmployee.objects.filter(full_name__icontains=name).first()
            if not emp:
                print(f"❌ OrganizationEmployee {name} not found!")
                continue
            
            # 1. Clear cache
            emp.invalidate_permission_cache()
            
            # 2. Get Effective Permission Map
            user_perms_map = emp.get_final_permissions()
            print(f"Employee Effective Capabilities: {sorted(list(user_perms_map.keys()))}")
            
            # 3. Build Full Org Tree
            subscription_owner = emp.organization.verified_user
            full_tree = _build_permission_tree(subscription_owner, request=None)
            
            print("\nResolved Sidebar Modules:")
            found_any = False
            for service in full_tree:
                for cat in service.get('categories', []):
                    cat_key = cat.get('linked_capability') or cat.get('category_key')
                    if cat_key in user_perms_map:
                        found_any = True
                        perms = user_perms_map.get(cat_key, {})
                        print(f" - {cat.get('name')} ({cat_key}) | View={perms.get('can_view')} | Create={perms.get('can_create')} | Edit={perms.get('can_edit')}")
            
            if not found_any:
                print(" 📭 NO ACCESSIBLE MODULES.")

        except Exception as e:
            print(f"Error for {name}: {e}")

if __name__ == "__main__":
    verify_employees()
