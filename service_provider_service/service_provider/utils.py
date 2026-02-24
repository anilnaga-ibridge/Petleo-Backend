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

def _build_permission_tree(user, request=None):
    """
    Reconstructs the full permission tree for a user based on ProviderCapabilityAccess.
    Returns a list of Service objects with nested Categories and Facilities.
    """
    def _get_abs_url(media_file):
        if not media_file:
            return None
        if request:
            return request.build_absolute_uri(media_file.url)
        return media_file.url

    # 1. Fetch direct capability records
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    logger.info(f"DEBUG: Building Tree for {user.auth_user_id} | Raw Caps Found: {caps.count()}")
    
    # 2. Gather all relevant Template IDs
    service_ids = set()
    category_ids = set()
    facility_ids = set()
    pricing_ids = set()
    
    for cap in caps:
        if cap.service_id: service_ids.add(cap.service_id)
        if cap.category_id: category_ids.add(cap.category_id)
        if cap.facility_id: facility_ids.add(cap.facility_id)
        if cap.pricing_id: pricing_ids.add(cap.pricing_id)

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

    pricing_tmpls = {
        bg.super_admin_pricing_id: bg 
        for bg in ProviderTemplatePricing.objects.filter(super_admin_pricing_id__in=pricing_ids)
    }

    # 4. FETCH CUSTOM PRICING OVERRIDES
    from provider_dynamic_fields.models import ProviderPricing
    custom_pricing = {
        (p.service_id, p.category_id, str(p.facility.id) if p.facility else None): p
        for p in ProviderPricing.objects.filter(provider=user, is_active=True)
    }

    # 5. Build Tree
    # Structure: ServiceUUID -> { data, categories: { CategoryUUID -> { data, facilities: { ... } } } }
    tree = {}

    # Sort caps so those with pricing_id come later (if any), 
    # but the logic below is now robust enough to handle pricing updates even if node exists.
    for cap in caps:
        sid = cap.service_id
        if not sid:
            continue
            
        # -- Service Node --
        if sid not in tree:
            tmpl = service_tmpls.get(sid)
            if not tmpl:
                continue
                
            tree[sid] = {
                "service_id": sid,
                "service_name": tmpl.display_name,
                "name": tmpl.display_name,
                "service_key": tmpl.name.replace(" ", "_").upper(),
                "icon": tmpl.icon,
                "can_view": False,
                "can_create": False,
                "can_edit": False,
                "can_delete": False,
                "categories": {}
            }
        
        cid = cap.category_id
        if not cid:
            _merge_perms(tree[sid], cap)
            continue
            
        # -- Category Node --
        if cid not in tree[sid]["categories"]:
            tmpl = category_tmpls.get(cid)
            tree[sid]["categories"][cid] = {
                "category_id": cid,
                "category_name": tmpl.name if tmpl else "Unknown Category",
                "name": tmpl.name if tmpl else "Unknown Category",
                "linked_capability": tmpl.linked_capability if tmpl else None,
                "category_key": (tmpl.linked_capability or tmpl.name) if tmpl else None,
                "can_view": False,
                "can_create": False,
                "can_edit": False,
                "can_delete": False,
                "facilities": {}
            }
        
        fid = cap.facility_id
        if not fid:
            _merge_perms(tree[sid]["categories"][cid], cap)
            tree[sid]["can_view"] = True
            tree[sid]["categories"][cid]["can_view"] = True
            continue
            
        # -- Facility Node --
        if fid not in tree[sid]["categories"][cid]["facilities"]:
            tmpl = facility_tmpls.get(fid)
            tree[sid]["categories"][cid]["facilities"][fid] = {
                "facility_id": fid,
                "facility_name": tmpl.name if tmpl else "Unknown Facility",
                "name": tmpl.name if tmpl else "Unknown Facility",
                "can_view": False,
                "can_create": False,
                "can_edit": False,
                "can_delete": False,
                "price": "0.00",
                "duration": None,
                "description": "",
                "image_url": _get_abs_url(tmpl.image) if tmpl else None,
                "gallery": [_get_abs_url(img.image) for img in tmpl.gallery.all()] if tmpl and hasattr(tmpl, 'gallery') else []
            }
        
        # --- RESOLVE PRICING ---
        # 1. Start with existing data (might have been set by a previous cap record)
        target_fac = tree[sid]["categories"][cid]["facilities"][fid]
        
        # 2. Check for Custom Override (Highest Priority)
        custom_key = (sid, cid, fid)
        if custom_key in custom_pricing:
            p_custom = custom_pricing[custom_key]
            target_fac["price"] = str(p_custom.price)
            target_fac["duration"] = p_custom.duration_minutes
            target_fac["description"] = p_custom.description
            target_fac["pricing_id"] = f"CUSTOM_{p_custom.id}"
        
        # 3. Check for Template Pricing (Fallback)
        # Note: We ONLY update if price is "0.00" or we haven't found a custom one yet
        elif cap.pricing_id:
            p_tmpl = pricing_tmpls.get(cap.pricing_id)
            if p_tmpl:
                # Only overwrite if we don't already have a custom price 
                # (pricing_id starting with CUSTOM_ indicates override)
                if not str(target_fac.get("pricing_id", "")).startswith("CUSTOM_"):
                    target_fac["price"] = str(p_tmpl.price)
                    target_fac["duration"] = p_tmpl.duration_minutes
                    target_fac["description"] = p_tmpl.description
                    target_fac["pricing_id"] = cap.pricing_id

        if target_fac:
            _merge_perms(target_fac, cap)
            # Ensure parents are viewable if a child is granted
            tree[sid]["can_view"] = tree[sid].get("can_view", False) or cap.can_view
            tree[sid]["categories"][cid]["can_view"] = tree[sid]["categories"][cid].get("can_view", False) or cap.can_view

    # 5b. FETCH AND ATTACH ADD-ONS
    # Collect all facility Super Admin IDs currently in the tree related to their nodes
    facility_node_map = {}
    for s_data in tree.values():
        for c_data in s_data["categories"].values():
            for f_id, f_data in c_data["facilities"].items():
                facility_node_map[f_id] = f_data
                if "addons" not in f_data:
                    f_data["addons"] = []

    if facility_node_map:
        # Fetch add-ons where parent is in our list
        addons = ProviderTemplateFacility.objects.filter(
            parent_facility__super_admin_facility_id__in=facility_node_map.keys(),
            is_addon=True
        ).select_related('parent_facility').prefetch_related('pricing_rules')

        for addon in addons:
            parent_id = addon.parent_facility.super_admin_facility_id
            if parent_id in facility_node_map:
                pricing = addon.pricing_rules.first() # Default to first rule if any
                addon_data = {
                    "id": str(addon.id), # Internal UUID
                    "super_admin_id": addon.super_admin_facility_id,
                    "name": addon.name,
                    "description": addon.description,
                    "price": str(pricing.price) if pricing else "0.00",
                    "duration": pricing.duration_minutes if pricing else None
                }
                facility_node_map[parent_id]["addons"].append(addon_data)

    # 6. MERGE CUSTOM CATEGORIES & FACILITIES
    # Custom categories created by the provider exist in ProviderCategory table
    # but may not have ProviderCapabilityAccess records
    from provider_dynamic_fields.models import ProviderCategory, ProviderFacility, ProviderPricing
    
    custom_categories = ProviderCategory.objects.filter(provider=user, is_active=True).select_related('provider')
    for cat in custom_categories:
        sid = cat.service_id
        if not sid or sid not in tree:
            continue
            
        cid = str(cat.id)
        
        # Only add if not already present
        if cid not in tree[sid]["categories"]:
            tree[sid]["categories"][cid] = {
                "category_id": cid,
                "category_name": cat.name,
                "name": cat.name,
                "linked_capability": None,
                "category_key": cat.name,
                "can_view": True,  # Provider owns this, so they can view it
                "can_create": True,
                "can_edit": True,
                "can_delete": True,
                "facilities": {}
            }
            tree[sid]["can_view"] = True
        
        # Fetch custom facilities for this category
        custom_facilities = ProviderFacility.objects.filter(category=cat, is_active=True)
        for fac in custom_facilities:
            fid = str(fac.id)
            if fid not in tree[sid]["categories"][cid]["facilities"]:
                # Get pricing if exists
                pricing = ProviderPricing.objects.filter(
                    provider=user,
                    service_id=sid,
                    category_id=cid,
                    facility_id=fid,
                    is_active=True
                ).first()
                
                tree[sid]["categories"][cid]["facilities"][fid] = {
                    "facility_id": fid,
                    "facility_name": fac.name,
                    "name": fac.name,
                    "can_view": True,
                    "can_create": True,
                    "can_edit": True,
                    "can_delete": True,
                    "price": str(pricing.price) if pricing else str(fac.price),
                    "duration": pricing.duration if pricing else None,
                    "description": fac.description or "",
                    "image_url": _get_abs_url(fac.image),
                    "gallery": [_get_abs_url(img.image) for img in fac.gallery_images.all()] if hasattr(fac, 'gallery_images') else [],
                    "pricing_id": str(pricing.id) if pricing else None
                }

    # 7. Flatten to List
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

def get_user_dynamic_location(user):
    """
    Fetches the dynamic 'Location' field value for a user.
    Robust version: searches all 'Location' definitions to handle role mismatches.
    """
    from provider_dynamic_fields.models import ProviderFieldValue, LocalFieldDefinition
    try:
        # 1. Find all definitions for "Location" (any target)
        loc_defs = LocalFieldDefinition.objects.filter(name="Location")
        if not loc_defs.exists():
             return None
             
        # 2. Check if user has a value for ANY of these definitions
        val_obj = ProviderFieldValue.objects.filter(
            verified_user=user, 
            field_id__in=loc_defs.values_list('id', flat=True)
        ).first()
        
        if val_obj and val_obj.value:
            return str(val_obj.value)
    except Exception:
        pass
    return None
