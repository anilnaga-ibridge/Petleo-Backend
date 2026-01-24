from django.utils import timezone
from django.db import transaction
from .models import PurchasedPlan, ProviderPlanCapability
from .kafka_producer import publish_permissions_updated
from .services import assign_plan_permissions_to_user

def purchase_plan_and_publish(user, plan, billing_cycle="MONTHLY"):
    """
    Creates PurchasedPlan, assigns permissions (DB), and publishes Kafka event.
    Use this instead of directly calling PurchasedPlan.objects.create(...) in the view.
    """
    with transaction.atomic():
        # Ensure billing_cycle is a string
        if hasattr(billing_cycle, 'code'):
             billing_cycle = billing_cycle.code
             
        purchased = PurchasedPlan.objects.create(user=user, plan=plan, billing_cycle=billing_cycle)
        # assign permissions in DB (your existing function)
        assign_plan_permissions_to_user(user, plan)

        # build permissions payload from ProviderPlanCapability rows we've just created
        perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)
        perms_payload = []
        for p in perms:
            # Safely get booleans from JSON field
            can_view = p.permissions.get("can_view", False) if p.permissions else False
            can_create = p.permissions.get("can_create", False) if p.permissions else False
            can_edit = p.permissions.get("can_edit", False) if p.permissions else False
            can_delete = p.permissions.get("can_delete", False) if p.permissions else False

            perms_payload.append({
                "plan_id": str(p.plan.id),
                "service_id": str(p.service.id) if p.service else None,
                "service_name": getattr(p.service, "display_name", None),
                "category_id": str(p.category.id) if p.category else None,
                "category_name": getattr(p.category, "name", None),
                "facility_id": str(p.facility.id) if p.facility else None,
                "facility_name": getattr(p.facility, "name", None),
                "linked_capability": getattr(p.category, "linked_capability", None) if p.category else None,
                "can_view": can_view,
                "can_create": can_create,
                "can_edit": can_edit,
                "can_delete": can_delete,
            })

        # Collect templates
        templates = {
            "services": [],
            "categories": [],
            "facilities": [],
            "pricing": []
        }
        
        # Helper to avoid duplicates
        seen_services = set()
        seen_categories = set()
        seen_facilities = set()
        
        # 1. Collect from PlanCapability (Permissions)
        for p in perms:
            if p.service and p.service.id not in seen_services:
                templates["services"].append({
                    "id": str(p.service.id),
                    "name": p.service.name,
                    "display_name": p.service.display_name,
                    "icon": getattr(p.service, "icon", "tabler-box")
                })
                seen_services.add(p.service.id)
            
        # 1.5 Fetch ALL Categories and Facilities for the seen services
        from dynamic_categories.models import Category
        from dynamic_facilities.models import Facility
        
        # Fetch all categories for these services
        all_cats = Category.objects.filter(service__id__in=seen_services)
        for cat in all_cats:
            if cat.id not in seen_categories:
                templates["categories"].append({
                    "id": str(cat.id),
                    "service_id": str(cat.service.id),
                    "name": cat.name,
                    "linked_capability": cat.linked_capability,
                    "is_template": True
                })
                seen_categories.add(cat.id)
        
        # Fetch all facilities for these services
        all_facs = Facility.objects.filter(service__id__in=seen_services)
        
        # Build map of service_id -> list of category_ids
        service_to_cat_map = {}
        for cat_data in templates["categories"]:
            s_id = cat_data["service_id"]
            if s_id not in service_to_cat_map:
                service_to_cat_map[s_id] = []
            service_to_cat_map[s_id].append(cat_data["id"])
            
        for fac in all_facs:
            s_id = str(fac.service.id)
            # Find a category to attach to
            cats = service_to_cat_map.get(s_id, [])
            if not cats:
                # No categories for this service, cannot attach facility in current Consumer logic
                continue
                
            # Attach to the first category found
            target_cat_id = cats[0]
            
            # Check for duplicates or just add?
            # Since we attach to only one category, simple check is enough
            if fac.id not in seen_facilities:
                templates["facilities"].append({
                    "id": str(fac.id),
                    "category_id": target_cat_id,
                    "name": fac.name,
                    "description": getattr(fac, "description", "")
                })
                seen_facilities.add(fac.id)

        # 2. Collect Pricing (Pricing model)
        from dynamic_pricing.models import PricingRule
        
        pricing_qs = PricingRule.objects.filter(service__id__in=seen_services, is_active=True)
        
        for price in pricing_qs:
            p_cat_id = str(price.category.id) if price.category else None
            p_fac_id = str(price.facility.id) if price.facility else None
            
            include_price = False
            if not p_cat_id and not p_fac_id:
                include_price = True
            elif p_cat_id and not p_fac_id:
                if price.category.id in seen_categories:
                    include_price = True
            elif p_fac_id:
                if price.facility.id in seen_facilities:
                    include_price = True
            
            if include_price:
                templates["pricing"].append({
                    "id": str(price.id),
                    "service_id": str(price.service.id),
                    "category_id": p_cat_id,
                    "facility_id": p_fac_id,
                    "price": str(price.base_price), # PricingRule has base_price, not price
                    "duration": price.duration_minutes or 0, # Handle None
                    "description": f"Default pricing for {price.service.display_name}"
                })

        purchased_plan_info = {
            "id": str(purchased.id),
            "plan_id": str(plan.id),
            "billing_cycle_id": None, 
            "start_date": purchased.start_date.isoformat(),
            "end_date": purchased.end_date.isoformat() if purchased.end_date else None,
        }

        # auth_user_id: use the ID ServiceProvider expects.
        if hasattr(user, 'auth_user_id') and user.auth_user_id:
            auth_user_id = str(user.auth_user_id)
        else:
            auth_user_id = str(user.id)

        # -------------------------------------------
        # DYNAMIC PERMISSIONS SYNC
        # -------------------------------------------
        from dynamic_permissions.models import PlanCapability as DynPlanCapability, ProviderCapability as DynProviderCapability
        from admin_core.models import VerifiedUser

        dynamic_caps_payload = []
        
        # Resolve VerifiedUser instance
        verified_user_instance = VerifiedUser.objects.filter(auth_user_id=auth_user_id).first()
        print(f"DEBUG: VerifiedUser lookup for {auth_user_id} -> {verified_user_instance}")
        
        if verified_user_instance:
             # Find DB Plan Capabilities
             dyn_caps = DynPlanCapability.objects.filter(plan=plan)
             print(f"DEBUG: DynPlanCapability count for plan {plan.id}: {dyn_caps.count()}")
             for dc in dyn_caps:
                 DynProviderCapability.objects.update_or_create(
                     user=verified_user_instance,
                     capability=dc.capability,
                     defaults={'is_active': True}
                 )
                 
                 # Add to payload
                 modules = dc.capability.modules.filter(is_active=True).values('key', 'name', 'route', 'icon', 'sequence')
                 dynamic_caps_payload.append({
                     "capability_key": dc.capability.key,
                     "modules": list(modules)
                 })
        
        print(f"DEBUG: Dynamic Caps Payload Size: {len(dynamic_caps_payload)}")
                 
        publish_permissions_updated(auth_user_id, str(purchased.id), perms_payload, purchased_plan_info, templates=templates, dynamic_capabilities=dynamic_caps_payload)

    return purchased
