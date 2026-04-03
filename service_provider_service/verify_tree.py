import os
import django
import sys
import json

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from service_provider.utils import _build_permission_tree

def verify_sidebar_tree(email):
    print(f"--- Verifying Sidebar Tree for {email} ---")
    try:
        user = VerifiedUser.objects.get(email=email)
        print(f"User Found: {user.email} (AuthID: {user.auth_user_id})")
        
        from provider_dynamic_fields.models import ProviderCapabilityAccess
        caps = ProviderCapabilityAccess.objects.filter(user=user)
        print(f"Raw Caps for user: {caps.count()}")
        for c in caps:
            print(f"  Cap: S={c.service_id}, C={c.category_id}, F={c.facility_id}")

        from service_provider.utils import _build_permission_tree
        tree_list = _build_permission_tree(user)
        
        print(f"\nTree Result: {len(tree_list)} services found.")
        for svc in tree_list:
            print(f"Service: {svc['service_name']} (Key: {svc['service_key']})")
            for cat in svc.get('categories', []):
                print(f"  Category: {cat['category_name']} (Key: {cat['category_key']})")
                for fac in cat.get('facilities', []):
                    print(f"    Facility: {fac['facility_name']}")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    verify_sidebar_tree('madhu@gmail.com')
