# plans_coupens/services.py
from django.db import transaction
from .models import ProviderPlanCapability
import calendar
from datetime import timedelta

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)

def calculate_end_date(start_date, value, unit):
    if unit == "days":
        return start_date + timedelta(days=value)
    elif unit == "weeks":
        return start_date + timedelta(weeks=value)
    elif unit == "months":
        return add_months(start_date, value)
    elif unit == "years":
        return add_months(start_date, value * 12)
    return None

def assign_plan_permissions_to_user(user, plan):
    """
    Copy all PlanCapability templates into ProviderPlanCapability for `user`.
    """
    with transaction.atomic():
        # Optionally you might want to delete existing permissions for the same plan/user
        ProviderPlanCapability.objects.filter(user=user, plan=plan).delete()

        for cap in plan.capabilities.all():
            ProviderPlanCapability.objects.create(
                user=user,
                plan=plan,
                service=cap.service,
                category=cap.category,
                facility=cap.facility,
                can_view=cap.can_view,
                can_create=cap.can_create,
                can_edit=cap.can_edit,
                can_delete=cap.can_delete,
            )


# superadmin/purchase_publish_wrapper.py
from django.utils import timezone
from django.db import transaction
from .models import PurchasedPlan, ProviderPlanCapability
from .kafka_producer import publish_permissions_updated
# make sure assign_plan_permissions_to_user is imported where available

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
                "linked_capability": getattr(p.category, "linked_capability", None) if p.category else None,
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
