# plans_coupens/services.py
from django.db import transaction
from .models import ProviderPlanPermission

def assign_plan_permissions_to_user(user, plan):
    """
    Copy all PlanItem templates into ProviderPlanPermission for `user`.
    """
    with transaction.atomic():
        # Optionally you might want to delete existing permissions for the same plan/user
        ProviderPlanPermission.objects.filter(user=user, plan=plan).delete()

        for item in plan.items.all():
            perm = ProviderPlanPermission.objects.create(
                user=user,
                plan=plan,
                service=item.service,
                category=item.category,
                can_view=item.can_view,
                can_create=item.can_create,
                can_edit=item.can_edit,
                can_delete=item.can_delete,
            )
            # copy many-to-many facilities
            perm.facilities.set(item.facilities.all())



# superadmin/purchase_publish_wrapper.py
from django.utils import timezone
from django.db import transaction
from .models import PurchasedPlan, ProviderPlanPermission
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

        # build permissions payload from ProviderPlanPermission rows we've just created
        perms = ProviderPlanPermission.objects.filter(user=user, plan=plan).prefetch_related("facilities")
        perms_payload = []
        for p in perms:
            perms_payload.append({
                "plan_id": str(p.plan.id),
                "service_id": str(p.service.id) if p.service else None,
                "service_name": getattr(p.service, "display_name", None),
                "category_id": str(p.category.id) if p.category else None,
                "category_name": getattr(p.category, "name", None),
                "can_view": bool(p.can_view),
                "can_create": bool(p.can_create),
                "can_edit": bool(p.can_edit),
                "can_delete": bool(p.can_delete),
                "facilities": [f.name for f in p.facilities.all()],
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
