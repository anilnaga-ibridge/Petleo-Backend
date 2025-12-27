import os
import django
import sys
import json
from django.conf import settings

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility, 
    ProviderTemplatePricing,
    ProviderCapabilityAccess
)
from django.db import transaction

def debug_consumer():
    print("--- Debugging Consumer Logic ---")
    
    # 1. Get Latest User
    user = VerifiedUser.objects.order_by('-created_at').first()
    if not user:
        print("No user found.")
        return
    
    print(f"User: {user.email} ({user.auth_user_id})")
    
    # 2. Mock Payload (Simulating what Super Admin sends)
    # We'll use dummy IDs but valid structure
    mock_plan_id = "test-plan-123"
    
    # Fetch existing templates to use real IDs if possible, or just use dummy ones
    # For this test, let's assume templates are already synced (since we saw them in inspection)
    # We will try to create permissions based on existing templates.
    
    templates = {
        "services": [{"id": "svc-1", "name": "Test Service", "display_name": "Test Service"}],
        "categories": [{"id": "cat-1", "service_id": "svc-1", "name": "Test Category"}],
        "facilities": [{"id": "fac-1", "category_id": "cat-1", "name": "Test Facility"}],
        "pricing": [{"id": "price-1", "service_id": "svc-1", "category_id": "cat-1", "facility_id": "fac-1", "price": "100.00", "duration": "per_hour"}]
    }
    
    purchased_plan = {
        "plan_id": mock_plan_id,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2025-01-01T00:00:00Z"
    }
    
    permissions_list = [] # Empty explicit permissions
    
    print("Running sync logic...")
    
    try:
        with transaction.atomic():
            # 1. SYNC TEMPLATES
            print("Syncing Templates...")
            for svc in templates.get("services", []):
                ProviderTemplateService.objects.update_or_create(
                    super_admin_service_id=svc["id"],
                    defaults={"name": svc["name"], "display_name": svc["display_name"]}
                )
            
            for cat in templates.get("categories", []):
                service_obj = ProviderTemplateService.objects.get(super_admin_service_id=cat["service_id"])
                ProviderTemplateCategory.objects.update_or_create(
                    super_admin_category_id=cat["id"],
                    defaults={"service": service_obj, "name": cat["name"]}
                )
                
            for fac in templates.get("facilities", []):
                cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=fac["category_id"])
                ProviderTemplateFacility.objects.update_or_create(
                    super_admin_facility_id=fac["id"],
                    defaults={"category": cat_obj, "name": fac["name"]}
                )
                
            for price in templates.get("pricing", []):
                service_obj = ProviderTemplateService.objects.get(super_admin_service_id=price["service_id"])
                cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=price["category_id"])
                fac_obj = ProviderTemplateFacility.objects.get(super_admin_facility_id=price["facility_id"])
                
                ProviderTemplatePricing.objects.update_or_create(
                    super_admin_pricing_id=price["id"],
                    defaults={
                        "service": service_obj,
                        "category": cat_obj,
                        "facility": fac_obj,
                        "price": price["price"],
                        "duration": price["duration"]
                    }
                )
            
            print("Templates Synced.")
            
            # 2. SYNC PERMISSIONS
            print("Syncing Permissions...")
            plan_id = purchased_plan.get("plan_id")
            
            # Clear old
            ProviderCapabilityAccess.objects.filter(user=user, plan_id=plan_id).delete()
            
            perms_map = {}
            
            def add_perm(s_id, c_id, f_id, p_id, **kwargs):
                key = (s_id, c_id, f_id, p_id)
                if key not in perms_map:
                    perms_map[key] = {
                        "service_id": s_id,
                        "category_id": c_id,
                        "facility_id": f_id,
                        "pricing_id": p_id,
                        "can_view": True,
                        "can_create": False,
                        "can_edit": False,
                        "can_delete": False
                    }
                perms_map[key].update(kwargs)

            # Auto-generate
            for svc in templates.get("services", []):
                add_perm(svc["id"], None, None, None)
                
            cat_service_map = {}
            for cat in templates.get("categories", []):
                cat_service_map[cat["id"]] = cat["service_id"]
                add_perm(cat["service_id"], cat["id"], None, None)
                
            for fac in templates.get("facilities", []):
                s_id = cat_service_map.get(fac["category_id"])
                if s_id:
                    add_perm(s_id, fac["category_id"], fac["id"], None)
                else:
                    print(f"WARNING: Could not resolve Service ID for facility {fac['name']}")

            for price in templates.get("pricing", []):
                add_perm(price["service_id"], price["category_id"], price["facility_id"], price["id"])

            # Create objects
            new_perms = []
            for p_data in perms_map.values():
                new_perms.append(ProviderCapabilityAccess(
                    user=user,
                    plan_id=plan_id,
                    service_id=p_data["service_id"],
                    category_id=p_data["category_id"],
                    facility_id=p_data["facility_id"],
                    pricing_id=p_data["pricing_id"],
                    can_view=p_data["can_view"],
                    can_create=p_data["can_create"],
                    can_edit=p_data["can_edit"],
                    can_delete=p_data["can_delete"],
                ))
            
            if new_perms:
                print(f"Creating {len(new_perms)} permissions...")
                ProviderCapabilityAccess.objects.bulk_create(new_perms)
                print("Permissions Created.")
            else:
                print("No permissions to create.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_consumer()
