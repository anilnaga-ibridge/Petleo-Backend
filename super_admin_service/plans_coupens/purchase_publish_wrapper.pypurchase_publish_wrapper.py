# plans_coupons/purchase_publish_wrapper.py

from django.db import transaction
from django.utils import timezone

from .models import PurchasedPlan, ProviderPlanPermission
from .services import assign_plan_permissions_to_user
from .kafka_producer import publish_permissions_event


def purchase_plan_and_publish(user, plan, billing_cycle=None):
    """
    Used by purchase_plan view.
    - Creates PurchasedPlan
    - Assigns permissions
    - Publishes Kafka "provider.permissions.updated" event
    """

    with transaction.atomic():
        purchase = PurchasedPlan.objects.create(
            user=user,
            plan=plan,
            billing_cycle=billing_cycle,
            start_date=timezone.now()
        )

        # Assign permissions in SuperAdmin DB
        assign_plan_permissions_to_user(user, plan)

        # Build event payload
        assigned_permissions = ProviderPlanPermission.objects.filter(user=user, plan=plan)

        permissions_list = []
        for p in assigned_permissions:
            permissions_list.append({
                "service_id": str(p.service_id) if p.service_id else None,
                "category_id": str(p.category_id) if p.category_id else None,
                "can_view": p.can_view,
                "can_create": p.can_create,
                "can_edit": p.can_edit,
                "can_delete": p.can_delete,
                "facilities": [str(f.id) for f in p.facilities.all()],
            })

        event_payload = {
            "event": "provider.permissions.updated",
            "timestamp": timezone.now().isoformat(),
            "data": {
                "auth_user_id": str(user.id),  # Important: your VerifiedUser.auth_user_id maps to Auth user ID
                "plan_id": str(plan.id),
                "permissions": permissions_list,
                "billing_cycle_id": billing_cycle.id if billing_cycle else None,
            }
        }

        # Publish event to Kafka
        publish_permissions_event(event_payload)

    return purchase
