import logging
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess,
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility,
    ProviderTemplatePricing
)
# We don't need OrganizationEmployee/ServiceProvider for this util specifically
# unless we wanted to expand logic, but simpler is better for recovery.

logger = logging.getLogger(__name__)

def _build_permission_tree(user):
    """
    Reconstructs the full permission tree for a user based on ProviderCapabilityAccess.
    Returns a list of Service objects with nested Categories and Facilities.
    """
    # 1. Fetch direct capability records
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    logger.info(f"DEBUG: Building Tree for {user.auth_user_id} | Raw Caps Found: {caps.count()}")
    
    # 2. Gather all relevant Template IDs
    service_ids = set()
    category_ids = set()
    facility_ids = set()
    
    for cap in caps:
        if cap.service_id: service_ids.add(cap.service_id)
        if cap.category_id: category_ids.add(cap.category_id)
        if cap.facility_id: facility_ids.add(cap.facility_id)

    # 3. Fetch Templates (bulk)
    # Note: IDs in CapabilityAccess are strings matching super_admin_X_id
    service_tmpls = {
        bg.super_admin_service_id: bg 
        for bg in ProviderTemplateService.objects.filter(super_admin_service_id__in=service_ids)
    }
    category_tmpls = {
        bg.super_admin_category_id: bg 
        for bg in ProviderTemplateCategory.objects.filter(super_admin_category_id__in=category_ids)
    }
    facility_tmpls = {
        bg.super_admin_facility_id: bg 
        for bg in ProviderTemplateFacility.objects.filter(super_admin_facility_id__in=facility_ids)
    }

    # 4. Build Tree
    # Structure: ServiceUUID -> { data, categories: { CategoryUUID -> { data, facilities: { ... } } } }
    tree = {}

    for cap in caps:
        sid = cap.service_id
        if not sid:
            continue
            
        # -- Service Node --
        if sid not in tree:
            tmpl = service_tmpls.get(sid)
            if not tmpl:
                # [FIX] Skip if template is missing to avoid "Unknown Service" tiles
                continue
                
            tree[sid] = {
                "service_id": sid,
                "service_name": tmpl.display_name,
                "name": tmpl.display_name, # Frontend compatibility
                "service_key": tmpl.name.upper(),
                "icon": tmpl.icon,
                "can_view": False,
                "can_create": False,
                "can_edit": False,
                "can_delete": False,
                "categories": {}
            }
        
        cid = cap.category_id
        if not cid:
            # Direct Service Permission
            _merge_perms(tree[sid], cap)
            continue
            
        # -- Category Node --
        if cid not in tree[sid]["categories"]:
            tmpl = category_tmpls.get(cid)
            tree[sid]["categories"][cid] = {
                "category_id": cid,
                "category_name": tmpl.name if tmpl else "Unknown Category",
                "name": tmpl.name if tmpl else "Unknown Category", # Frontend compatibility
                "linked_capability": tmpl.linked_capability if tmpl else None,
                "category_key": tmpl.linked_capability if tmpl else None, # ✅ Used for deep search in frontend
                "can_view": False,
                "can_create": False,
                "can_edit": False,
                "can_delete": False,
                "facilities": {}
            }
        
        fid = cap.facility_id
        if not fid:
            # Direct Category Permission
            _merge_perms(tree[sid]["categories"][cid], cap)
            # Implies parent view
            tree[sid]["can_view"] = True
            continue
            
        # -- Facility Node --
        if fid not in tree[sid]["categories"][cid]["facilities"]:
            tmpl = facility_tmpls.get(fid)
            tree[sid]["categories"][cid]["facilities"][fid] = {
                "facility_id": fid,
                "facility_name": tmpl.name if tmpl else "Unknown Facility",
                "name": tmpl.name if tmpl else "Unknown Facility", # Frontend compatibility
                "can_view": False,
                "can_create": False,
                "can_edit": False,
                "can_delete": False
            }
        
        # Direct Facility Permission
        _merge_perms(tree[sid]["categories"][cid]["facilities"][fid], cap)
        # Implies parents view
        tree[sid]["can_view"] = True
        tree[sid]["categories"][cid]["can_view"] = True

    # 5. Flatten to List
    result_list = []
    for s_id, s_data in tree.items():
        # Flatten categories
        cat_list = []
        for c_id, c_data in s_data["categories"].items():
            # Flatten facilities
            fac_list = list(c_data["facilities"].values())
            c_data["facilities"] = sorted(fac_list, key=lambda x: x["facility_name"])
            cat_list.append(c_data)
        
        s_data["categories"] = sorted(cat_list, key=lambda x: x["category_name"])
        result_list.append(s_data)
        
    return sorted(result_list, key=lambda x: x["service_name"])

def _merge_perms(target_dict, cap_obj):
    target_dict["can_view"] = target_dict["can_view"] or cap_obj.can_view
    target_dict["can_create"] = target_dict["can_create"] or cap_obj.can_create
    target_dict["can_edit"] = target_dict["can_edit"] or cap_obj.can_edit
    target_dict["can_delete"] = target_dict["can_delete"] or cap_obj.can_delete
