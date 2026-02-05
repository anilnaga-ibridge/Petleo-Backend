
import json
import logging
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility
from dynamic_pricing.models import PricingRule
from dynamic_permissions.models import PlanCapability as DynPlanCapability
from plans_coupens.models import ProviderPlanCapability

logger = logging.getLogger(__name__)

def build_unified_payload(user, plan, purchased_plan_id, auth_user_id):
    """
    Unified logic to build the full Kafka payload for a plan purchase/republish.
    Ensures that business services (Grooming, etc.) are included as dynamic capabilities.
    """
    # 1. build permissions payload from ProviderPlanCapability rows
    perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)
    perms_payload = []
    seen_services = set()
    
    for p in perms:
        if p.service:
            seen_services.add(p.service.id)
            
        perms_payload.append({
            "plan_id": str(p.plan.id),
            "service_id": str(p.service.id) if p.service else None,
            "service_name": getattr(p.service, "display_name", None),
            "category_id": str(p.category.id) if p.category else None,
            "category_name": getattr(p.category, "name", None),
            "facility_id": str(p.facility.id) if p.facility else None,
            "facility_name": getattr(p.facility, "name", None),
            "linked_capability": getattr(p.category, "linked_capability", None) if p.category else None,
            "can_view": p.permissions.get("can_view", True) if p.permissions else True,
            "can_create": p.permissions.get("can_create", False) if p.permissions else False,
            "can_edit": p.permissions.get("can_edit", False) if p.permissions else False,
            "can_delete": p.permissions.get("can_delete", False) if p.permissions else False,
        })

    # 2. Collect templates
    templates = {
        "services": [], "categories": [], "facilities": [], "pricing": []
    }
    
    # Use services from both perms and explicit template list
    for p in perms:
        if p.service and p.service.id not in [s["id"] for s in templates["services"]]:
            templates["services"].append({
                "id": str(p.service.id),
                "name": p.service.name,
                "display_name": p.service.display_name,
                "icon": getattr(p.service, "icon", "tabler-box")
            })

    # Fetch Categories/Facilities for these services
    categories_qs = Category.objects.filter(service__id__in=seen_services)
    seen_categories = set()
    for cat in categories_qs:
        templates["categories"].append({
            "id": str(cat.id),
            "service_id": str(cat.service.id),
            "name": cat.name,
            "linked_capability": cat.linked_capability,
            "is_template": True
        })
        seen_categories.add(cat.id)
        for fac in cat.facilities.filter(is_active=True):
            templates["facilities"].append({
                "id": str(fac.id),
                "category_id": str(cat.id),
                "name": fac.name,
                "description": getattr(fac, "description", "")
            })

    # Pricing
    pricing_qs = PricingRule.objects.filter(service__id__in=seen_services, is_active=True)
    for price in pricing_qs:
        p_cat_id = str(price.category.id) if price.category else None
        p_fac_id = str(price.facility.id) if price.facility else None
        if p_fac_id and not p_cat_id and price.facility.category:
            p_cat_id = str(price.facility.category.id)

        templates["pricing"].append({
            "id": str(price.id),
            "service_id": str(price.service.id),
            "category_id": p_cat_id,
            "facility_id": p_fac_id,
            "price": str(price.base_price),
            "duration": getattr(price, 'duration_minutes', 'fixed'),
            "description": f"Default pricing for {price.service.display_name}"
        })

    # 3. Dynamic Capabilities (The Tech Keys)
    dynamic_caps_payload = []
    
    # A. From explicit DynPlanCapability table
    dyn_caps = DynPlanCapability.objects.filter(plan=plan)
    for dc in dyn_caps:
        modules = dc.capability.modules.filter(is_active=True).values('key', 'name', 'route', 'icon', 'sequence')
        dynamic_caps_payload.append({
            "capability_key": dc.capability.key,
            "modules": list(modules)
        })

    # B. AUTO-INFER from Service Templates (100% Database-Driven)
    # All services now have linked_capability auto-generated via Service.save()
    
    from dynamic_services.models import Service
    service_ids = [s["id"] for s in templates["services"]]
    services = Service.objects.filter(id__in=service_ids)
    
    for svc in services:
        # All services MUST have linked_capability (auto-generated if not set)
        if svc.linked_capability:
            cap_key = svc.linked_capability
            logger.info(f"✨ Using DB-linked capability {cap_key} for service {svc.display_name}")
            
            # Add to payload if not already present
            if not any(dc["capability_key"] == cap_key for dc in dynamic_caps_payload):
                dynamic_caps_payload.append({
                    "capability_key": cap_key,
                    "modules": []  # Simple services don't need modules yet
                })
        else:
            # This should never happen due to auto-generation in Service.save()
            logger.warning(f"⚠️  Service '{svc.display_name}' missing linked_capability! Skipping.")

    return {
        "perms_payload": perms_payload,
        "templates": templates,
        "dynamic_capabilities": dynamic_caps_payload
    }
