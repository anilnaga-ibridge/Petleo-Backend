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
        # build unified payload bundle
        from .payload_builder import build_unified_payload
        data_bundle = build_unified_payload(user, plan, str(purchased.id), auth_user_id)
        
        perms_payload = data_bundle["perms_payload"]
        templates = data_bundle["templates"]
        dynamic_caps_payload = data_bundle["dynamic_capabilities"]

        purchased_plan_info = {
            "id": str(purchased.id),
            "plan_id": str(plan.id),
            "billing_cycle_id": None, 
            "start_date": purchased.start_date.isoformat(),
            "end_date": purchased.end_date.isoformat() if purchased.end_date else None,
        }

        publish_permissions_updated(auth_user_id, str(purchased.id), perms_payload, purchased_plan_info, templates=templates, dynamic_capabilities=dynamic_caps_payload)


    return purchased
