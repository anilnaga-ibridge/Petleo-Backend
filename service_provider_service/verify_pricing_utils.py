import os
import sys
import django
import uuid

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility, 
    ProviderTemplatePricing
)
from service_provider.utils import _build_permission_tree

def run_test():
    print("--- Starting Pricing Tree Verification ---")
    
    # IDs
    user_id = str(uuid.uuid4())
    sid = "s_test_pricing"
    cid = "c_test_pricing"
    fid = "f_test_pricing"
    pid = "p_test_pricing"
    
    # Cleanup (just in case)
    VerifiedUser.objects.filter(auth_user_id=user_id).delete()
    ProviderTemplateService.objects.filter(super_admin_service_id=sid).delete()
    
    try:
        # 1. Create Data
        user = VerifiedUser.objects.create(auth_user_id=user_id, email="test@pricing.verify")
        
        s1 = ProviderTemplateService.objects.create(super_admin_service_id=sid, name="S", display_name="Service")
        c1 = ProviderTemplateCategory.objects.create(super_admin_category_id=cid, service=s1, name="Category")
        f1 = ProviderTemplateFacility.objects.create(super_admin_facility_id=fid, category=c1, name="Facility")
        
        # Create Pricing Template
        p1 = ProviderTemplatePricing.objects.create(
            super_admin_pricing_id=pid,
            service=s1, category=c1, facility=f1,
            price=150.00,
            duration="60 min",
            description="Test Pricing"
        )
        
        # Create Access with Pricing ID
        ProviderCapabilityAccess.objects.create(
            user=user, plan_id="test_plan",
            service_id=sid, category_id=cid, facility_id=fid, pricing_id=pid,
            can_view=True
        )
        
        # 2. Build Tree
        tree = _build_permission_tree(user)
        
        # 3. Inspect
        if not tree:
            print("FAILURE: Tree is empty")
            return

        service_node = tree[0]
        cat_node = service_node["categories"][0]
        fac_node = cat_node["facilities"][0]
        
        print(f"Facility Node: {fac_node}")
        
        if "price" in fac_node and float(fac_node["price"]) == 150.0:
            print("SUCCESS: Price found!")
        else:
            print("FAILURE: Price missing or incorrect.")

        if "duration" in fac_node and fac_node["duration"] == "60 min":
             print("SUCCESS: Duration found!")
        else:
             print("FAILURE: Duration missing.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        VerifiedUser.objects.filter(auth_user_id=user_id).delete()
        ProviderTemplateService.objects.filter(super_admin_service_id=sid).delete()

if __name__ == "__main__":
    run_test()
