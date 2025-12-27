import os
import django
import json
from rest_framework.response import Response

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess,
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility
)

def get_my_permissions_sim(email):
    try:
        verified_user = VerifiedUser.objects.get(email=email)
        print(f"User: {verified_user.email}")
        
        if not hasattr(verified_user, 'capabilities'):
            print("No capabilities relation")
            return

        perms = verified_user.capabilities.all()
        print(f"Found {perms.count()} permissions")
        
        services_map = {s.super_admin_service_id: s for s in ProviderTemplateService.objects.all()}
        categories_map = {c.super_admin_category_id: c for c in ProviderTemplateCategory.objects.all()}
        facilities_map = {f.super_admin_facility_id: f for f in ProviderTemplateFacility.objects.all()}

        grouped = {}
        
        for perm in perms:
            if not perm.service_id: continue
                
            s_id = str(perm.service_id)
            svc_obj = services_map.get(s_id)
            svc_name = svc_obj.display_name if svc_obj else "Unknown Service"
            svc_icon = svc_obj.icon if svc_obj else "tabler-box"

            if s_id not in grouped:
                grouped[s_id] = {
                    "service_id": s_id,
                    "service_name": svc_name,
                    "icon": svc_icon,
                    "categories": {}
                }
            
            if perm.category_id:
                c_id = str(perm.category_id)
                cat_obj = categories_map.get(c_id)
                cat_name = cat_obj.name if cat_obj else "Unknown Category"

                if c_id not in grouped[s_id]["categories"]:
                    grouped[s_id]["categories"][c_id] = {
                        "id": c_id,
                        "name": cat_name,
                        "permissions": {"can_view": False},
                        "facilities": []
                    }
                
                if not perm.facility_id:
                    grouped[s_id]["categories"][c_id]["permissions"] = {
                        "can_view": perm.can_view,
                    }
                else:
                    f_id = str(perm.facility_id)
                    fac_obj = facilities_map.get(f_id)
                    fac_name = fac_obj.name if fac_obj else "Unknown Facility"
                    
                    grouped[s_id]["categories"][c_id]["facilities"].append({
                        "id": f_id,
                        "name": fac_name,
                        "permissions": {"can_view": perm.can_view}
                    })

        permissions_list = []
        for s_val in grouped.values():
            cats_list = []
            for c_val in s_val["categories"].values():
                cats_list.append(c_val)
            
            final_cats = []
            for c in cats_list:
                c_flat = {
                    "id": c["id"],
                    "name": c["name"],
                    "facilities": c["facilities"],
                    **c["permissions"]
                }
                final_cats.append(c_flat)

            permissions_list.append({
                "service_id": s_val["service_id"],
                "service_name": s_val["service_name"],
                "categories": final_cats,
            })

        print(json.dumps(permissions_list, indent=2))

    except Exception as e:
        print(f"Error: {e}")

print("\n--- Simulation for prem@gmail.com ---")
get_my_permissions_sim("prem@gmail.com")
