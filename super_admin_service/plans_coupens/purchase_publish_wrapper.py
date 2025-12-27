# superadmin/purchase_publish_wrapper.py
from django.utils import timezone
from django.db import transaction
from .models import PurchasedPlan, ProviderPlanCapability
from .kafka_producer import publish_permissions_updated
# make sure assign_plan_permissions_to_user is imported where available
from .services import assign_plan_permissions_to_user

def purchase_plan_and_publish(user, plan, billing_cycle=None):
    """
    Creates PurchasedPlan, assigns permissions (DB), and publishes Kafka event.
    Use this instead of directly calling PurchasedPlan.objects.create(...) in the view.
    """
    with transaction.atomic():
        purchased = PurchasedPlan.objects.create(user=user, plan=plan, billing_cycle=billing_cycle)
        # assign permissions in DB (your existing function)
        assign_plan_permissions_to_user(user, plan)

        # build permissions payload from ProviderPlanCapability rows we've just created
        perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)
        perms_payload = []
        for p in perms:
            perms_payload.append({
                "plan_id": str(p.plan.id),
                "service_id": str(p.service.id) if p.service else None,
                "service_name": getattr(p.service, "display_name", None),
                "category_id": str(p.category.id) if p.category else None,
                "category_name": getattr(p.category, "name", None),
                "facility_id": str(p.facility.id) if p.facility else None,
                "facility_name": getattr(p.facility, "name", None),
                "can_view": bool(p.can_view),
                "can_create": bool(p.can_create),
                "can_edit": bool(p.can_edit),
                "can_delete": bool(p.can_delete),
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
            
            # We still collect explicit categories/facilities if they exist in perms
            # But we will ALSO fetch all children of seen_services below
            
        # 1.5 Fetch ALL Categories and Facilities for the seen services
        # This ensures that even if permission is Service-level, we send the full template structure
        from dynamic_categories.models import Category
        from dynamic_facilities.models import Facility
        
        # Fetch all categories for these services
        all_cats = Category.objects.filter(service__id__in=seen_services)
        for cat in all_cats:
            if cat.id not in seen_categories:
                templates["categories"].append({
                    "id": str(cat.id),
                    "service_id": str(cat.service.id),
                    "name": cat.name
                })
                seen_categories.add(cat.id)
        
        # Fetch all facilities for these categories
        all_facs = Facility.objects.filter(category__id__in=seen_categories)
        for fac in all_facs:
            if fac.id not in seen_facilities:
                templates["facilities"].append({
                    "id": str(fac.id),
                    "category_id": str(fac.category.id),
                    "name": fac.name,
                    "description": getattr(fac, "description", "")
                })
                seen_facilities.add(fac.id)

        # 2. Collect Pricing (Pricing model)
        from dynamic_pricing.models import Pricing
        
        # Fetch pricing for all involved services
        # We can filter by service__in=seen_services
        # But we also need to respect category/facility if they are set.
        # Let's just fetch all pricing for these services and filter in loop or let the consumer handle it.
        # Better: Fetch pricing that matches the services/categories/facilities we are sending.
        
        pricing_qs = Pricing.objects.filter(service__id__in=seen_services, is_active=True)
        
        for price in pricing_qs:
            # Only include if category/facility matches what we are sending (or is None)
            
            p_cat_id = str(price.category.id) if price.category else None
            p_fac_id = str(price.facility.id) if price.facility else None
            
            # Check if this pricing rule is relevant to the templates we are sending
            # If it's a service-level price (no cat, no fac), send it.
            # If it has cat, check if cat is in seen_categories.
            # If it has fac, check if fac is in seen_facilities.
            
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
                    "price": str(price.price),
                    "duration": price.duration,
                    "description": f"Default pricing for {price.service.display_name}"
                })

        purchased_plan_info = {
            "id": str(purchased.id),
            "plan_id": str(plan.id),
            "billing_cycle_id": purchased.billing_cycle.id if purchased.billing_cycle else None,
            "start_date": purchased.start_date.isoformat(),
            "end_date": purchased.end_date.isoformat() if purchased.end_date else None,
        }

        # auth_user_id: use the ID ServiceProvider expects.
        # SuperAdmin model has auth_user_id field which matches Auth Service ID.
        if hasattr(user, 'auth_user_id') and user.auth_user_id:
            auth_user_id = str(user.auth_user_id)
        else:
            auth_user_id = str(user.id)

        publish_permissions_updated(auth_user_id, str(purchased.id), perms_payload, purchased_plan_info, templates=templates)

    return purchased
