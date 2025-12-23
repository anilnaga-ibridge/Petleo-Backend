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

        purchased_plan_info = {
            "id": str(purchased.id),
            "plan_id": str(plan.id),
            "billing_cycle_id": purchased.billing_cycle.id if purchased.billing_cycle else None,
            "start_date": purchased.start_date.isoformat(),
            "end_date": purchased.end_date.isoformat() if purchased.end_date else None,
        }

        # auth_user_id: use the ID ServiceProvider expects; here we assume request.user.id
        # If ServiceProvider expects VerifiedUser.auth_user_id, ensure you send that value.
        auth_user_id = str(user.id)

        publish_permissions_updated(auth_user_id, str(purchased.id), perms_payload, purchased_plan_info)

    return purchased
