import os
import django
import json
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory, ProviderTemplateFacility

def debug_perms():
    print("--- Debugging get_my_permissions Logic (Direct JSON Dump) ---")
    
    user = VerifiedUser.objects.filter(email='nagaanil29@gmail.com').first()
    if not user:
        print("User not found")
        return

    print(f"User: {user.email}")
    
    # Replicate Logic from views.py
    perms = user.capabilities.all()
    services_map = {s.super_admin_service_id: s for s in ProviderTemplateService.objects.all()}
    categories_map = {c.super_admin_category_id: c for c in ProviderTemplateCategory.objects.all()}
    facilities_map = {f.super_admin_facility_id: f for f in ProviderTemplateFacility.objects.all()}

    grouped = {}
    for perm in perms:
        if not perm.service_id: continue
        s_id = str(perm.service_id)
        svc_obj = services_map.get(s_id)
        svc_name = svc_obj.display_name if svc_obj else "Unknown"
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
            cat_name = cat_obj.name if cat_obj else "Unknown"
            
            if c_id not in grouped[s_id]["categories"]:
                grouped[s_id]["categories"][c_id] = {
                    "id": c_id, "name": cat_name, 
                    "permissions": {
                        "can_view": False, "can_create": False, "can_edit": False, "can_delete": False
                    }, 
                    "facilities": []
                }
            
            if not perm.facility_id:
                grouped[s_id]["categories"][c_id]["permissions"]["can_view"] = perm.can_view
                grouped[s_id]["categories"][c_id]["permissions"]["can_create"] = perm.can_create
                grouped[s_id]["categories"][c_id]["permissions"]["can_edit"] = perm.can_edit
                grouped[s_id]["categories"][c_id]["permissions"]["can_delete"] = perm.can_delete
            else:
                f_id = str(perm.facility_id)
                grouped[s_id]["categories"][c_id]["facilities"].append({
                    "id": f_id, 
                    "permissions": {
                        "can_view": perm.can_view,
                        "can_create": perm.can_create,
                        "can_edit": perm.can_edit,
                        "can_delete": perm.can_delete
                    }
                })

    # Flatten structure for response
    permissions_list = []
    for s_val in grouped.values():
        cats_list = list(s_val["categories"].values())
        final_cats = []
        
        svc_can_view = False
        svc_can_create = False
        svc_can_edit = False
        svc_can_delete = False

        for c in cats_list:
            # Calculate effective can_view for category (bubble up from facilities)
            cat_effective_view = c["permissions"]["can_view"]
            for fac in c.get("facilities", []):
                if fac["permissions"]["can_view"]:
                    cat_effective_view = True

            c_flat = {
                "id": c["id"],
                "name": c["name"],
                "facilities": c["facilities"],
                **c["permissions"],
                "can_view": cat_effective_view # Override with effective view
            }
            final_cats.append(c_flat)
            
            # OR logic: if allowed in any category, allowed in service
            if cat_effective_view: svc_can_view = True
            if c["permissions"]["can_create"]: svc_can_create = True
            if c["permissions"]["can_edit"]: svc_can_edit = True
            if c["permissions"]["can_delete"]: svc_can_delete = True
            
            # Also check facility-level permissions
            for fac in c.get("facilities", []):
                if fac["permissions"]["can_view"]: svc_can_view = True
                if fac["permissions"]["can_create"]: svc_can_create = True
                if fac["permissions"]["can_edit"]: svc_can_edit = True
                if fac["permissions"]["can_delete"]: svc_can_delete = True

        permissions_list.append({
            "service_id": s_val["service_id"],
            "service_name": s_val["service_name"],
            "icon": s_val["icon"],
            "categories": final_cats,
            "can_view": svc_can_view,
            "can_create": svc_can_create,
            "can_edit": svc_can_edit,
            "can_delete": svc_can_delete
        })

    # Construct response
    response_data = {
        "permissions": permissions_list,
        "plan": {
            "title": "Active Plan", 
            "subtitle": "Standard Provider Plan",
            "end_date": timezone.now() + timezone.timedelta(days=30) 
        }
    }
    
    print("\n--- Full JSON Response ---")
    print(json.dumps(response_data, indent=2, default=str))

if __name__ == "__main__":
    debug_perms()
