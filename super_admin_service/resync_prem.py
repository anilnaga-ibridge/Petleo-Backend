import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from django.contrib.auth import get_user_model
from plans_coupens.models import PurchasedPlan, Plan
from plans_coupens.purchase_publish_wrapper import purchase_plan_and_publish
from plans_coupens.kafka_producer import publish_permissions_updated
from plans_coupens.services import assign_plan_permissions_to_user
from plans_coupens.models import ProviderPlanCapability

User = get_user_model()

def resync_prem():
    # prem@gmail.com ID from debug_individual_plans.py
    user_id = "ea2f2dee-1d1d-4f84-85fd-de08791f04a3"
    try:
        user = User.objects.get(id=user_id)
        print(f"Found user: {user.email}")
    except User.DoesNotExist:
        print("User not found")
        return

    # Find "basic paln" purchase
    try:
        plan = Plan.objects.get(title="basic paln")
        purchased = PurchasedPlan.objects.get(user=user, plan=plan)
        print(f"Found purchase: {purchased}")
    except (Plan.DoesNotExist, PurchasedPlan.DoesNotExist):
        print("Plan or Purchase not found")
        return

    # Manually trigger publish logic (copied from purchase_publish_wrapper but without creating new purchase)
    # We need to reconstruct the payload
    
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
    
    seen_services = set()
    seen_categories = set()
    seen_facilities = set()
    
    for p in perms:
        if p.service and p.service.id not in seen_services:
            templates["services"].append({
                "id": str(p.service.id),
                "name": p.service.name,
                "display_name": p.service.display_name,
                "icon": getattr(p.service, "icon", "tabler-box")
            })
            seen_services.add(p.service.id)
        
        if p.category and p.category.id not in seen_categories:
            templates["categories"].append({
                "id": str(p.category.id),
                "service_id": str(p.category.service.id),
                "name": p.category.name
            })
            seen_categories.add(p.category.id)
        
        if p.facility and p.facility.id not in seen_facilities:
            cat_id = str(p.category.id) if p.category else None
            if cat_id:
                templates["facilities"].append({
                    "id": str(p.facility.id),
                    "category_id": cat_id,
                    "name": p.facility.name,
                    "description": getattr(p.facility, "description", "")
                })
                seen_facilities.add(p.facility.id)

    purchased_plan_info = {
        "id": str(purchased.id),
        "plan_id": str(plan.id),
        "billing_cycle_id": purchased.billing_cycle.id if purchased.billing_cycle else None,
        "start_date": purchased.start_date.isoformat(),
        "end_date": purchased.end_date.isoformat() if purchased.end_date else None,
    }

    if hasattr(user, 'auth_user_id') and user.auth_user_id:
        auth_user_id = str(user.auth_user_id)
    else:
        auth_user_id = str(user.id)

    print(f"Publishing update for {auth_user_id}...")
    publish_permissions_updated(auth_user_id, str(purchased.id), perms_payload, purchased_plan_info, templates=templates)
    print("Done.")

if __name__ == "__main__":
    resync_prem()
