import os
import sys
import django
import json

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from service_provider.utils import _build_permission_tree

def debug_tree():
    # email = "nagaanil29@gmail.com"
    auth_id = "ec23848f-dd25-4701-805d-010cbc9e10fc"
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_id)
        print(f"User: {user.email}")
        
        # DEBUG LINKED CAPS
        caps = user.get_all_plan_capabilities()
        print(f"DEBUG: get_all_plan_capabilities -> {caps}")
        
        tree = _build_permission_tree(user)
        print(f"Tree Nodes: {len(tree)}")
        
        found_daycare = False
        for node in tree:
            name = node.get("service_name", "Unknown")
            key = node.get("service_key", "Unknown")
            view = node.get("can_view", False)
            print(f" - Service: {name} (Key: {key}) | Can View: {view}")
            
            if "DAY" in name.upper():
                found_daycare = True
                print(f"   >>> DAYCARE DETAILS: {json.dumps(node, indent=2)}")
        
        if not found_daycare:
            print("❌ Daycare Service NOT found in tree.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_tree()
