import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from service_provider.views import _build_permission_tree

def debug_tree():
    print("--- Debugging Permission Tree Output ---")
    
    user = VerifiedUser.objects.filter(email='ram@gmail.com').first()
    if not user:
        print("User not found")
        return

    print(f"User: {user.email}")
    
    # Call the actual function used by the view
    tree = _build_permission_tree(user)
    
    # Print summary
    print(f"Total Services in Tree: {len(tree)}")
    
    for svc in tree:
        print(f"\nService: {svc['service_name']} (ID: {svc['service_id']})")
        print(f"  - Can View: {svc['can_view']}")
        print(f"  - Categories: {len(svc['categories'])}")
        
        for cat in svc['categories']:
            print(f"    - Category: {cat['name']} (ID: {cat['id']})")
            print(f"      - Can View: {cat['can_view']}")
            print(f"      - Facilities: {len(cat['facilities'])}")
            print(f"      - Pricing: {len(cat['pricing'])}")

if __name__ == "__main__":
    debug_tree()
