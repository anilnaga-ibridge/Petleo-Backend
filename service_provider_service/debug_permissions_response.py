import os
import django
import sys
import json

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService, ProviderTemplateCategory, ProviderTemplateFacility

def debug_response():
    emp_id = "8ef65056-e082-4e56-bc57-4bf05f93aea0"
    print(f"--- Debugging Response for Employee {emp_id} ---")
    
    emp = OrganizationEmployee.objects.get(id=emp_id)
    user = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
    
    perms = ProviderCapabilityAccess.objects.filter(user=user)
    
    # Pre-fetch templates
    services_map = {str(s.super_admin_service_id): s for s in ProviderTemplateService.objects.all()}
    categories_map = {str(c.super_admin_category_id): c for c in ProviderTemplateCategory.objects.all()}
    facilities_map = {str(f.super_admin_facility_id): f for f in ProviderTemplateFacility.objects.all()}

    grouped = {}
    
    for perm in perms:
        if not perm.service_id:
            continue
            
        s_id = str(perm.service_id)
        svc_obj = services_map.get(s_id)
        svc_name = svc_obj.display_name if svc_obj else "Unknown Service"
        svc_icon = svc_obj.icon if svc_obj else "tabler-box"

        if s_id not in grouped:
            grouped[s_id] = {
                "service_id": s_id,
                "service_name": svc_name,
                "icon": svc_icon,
                "categories": {},
                "permissions": { "can_view": False, "can_create": False, "can_edit": False, "can_delete": False }
            }
        
        if perm.category_id:
            c_id = str(perm.category_id)
            cat_obj = categories_map.get(c_id)
            cat_name = cat_obj.name if cat_obj else "Unknown Category"

            if c_id not in grouped[s_id]["categories"]:
                grouped[s_id]["categories"][c_id] = {
                    "id": c_id,
                    "name": cat_name,
                    "permissions": { "can_view": False, "can_create": False, "can_edit": False, "can_delete": False },
                    "facilities": []
                }
            
            if not perm.facility_id:
                grouped[s_id]["categories"][c_id]["permissions"] = {
                    "can_view": perm.can_view,
                    "can_create": perm.can_create,
                    "can_edit": perm.can_edit,
                    "can_delete": perm.can_delete,
                }
            else:
                f_id = str(perm.facility_id)
                fac_obj = facilities_map.get(f_id)
                fac_name = fac_obj.name if fac_obj else "Unknown Facility"
                
                grouped[s_id]["categories"][c_id]["facilities"].append({
                    "id": f_id,
                    "name": fac_name,
                    "permissions": {
                        "can_view": perm.can_view,
                        "can_create": perm.can_create,
                        "can_edit": perm.can_edit,
                        "can_delete": perm.can_delete,
                    }
                })
        else:
            grouped[s_id]["root_permissions"] = {
                "can_view": perm.can_view,
                "can_create": perm.can_create,
                "can_edit": perm.can_edit,
                "can_delete": perm.can_delete,
            }

    # Flatten structure
    permissions_list = []
    for s_val in grouped.values():
        cats_list = []
        for c_val in s_val["categories"].values():
            cats_list.append(c_val)
        
        final_cats = cats_list # Simplified for debug
        
        permissions_list.append({
            "service_id": s_val["service_id"],
            "service_name": s_val["service_name"],
            "icon": s_val["icon"],
            "categories": final_cats,
            "permissions": s_val.get("root_permissions", {})
        })
        
    print(json.dumps(permissions_list, indent=2))

if __name__ == "__main__":
    debug_response()
