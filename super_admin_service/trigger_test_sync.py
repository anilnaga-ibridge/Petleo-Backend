import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import PurchasedPlan
from plans_coupens.payload_builder import build_unified_payload
from plans_coupens.kafka_producer import publish_permissions_updated

purchased = PurchasedPlan.objects.filter(user__email="nagaanil29@gmail.com").order_by("-start_date").first()
if purchased:
    print(f"Republishing for provider {purchased.user.email}, plan {purchased.plan.id}")
    auth_user_id = str(purchased.user.id)
    data_bundle = build_unified_payload(purchased.user, purchased.plan, str(purchased.id), auth_user_id)
    
    perms_payload = data_bundle["perms_payload"]
    templates = data_bundle["templates"]
    dynamic_caps = data_bundle["dynamic_capabilities"]

    purchased_plan_info = {
        "id": str(purchased.id),
        "plan_id": str(purchased.plan.id),
        "billing_cycle_id": None, 
        "start_date": purchased.start_date.isoformat(),
        "end_date": purchased.end_date.isoformat() if purchased.end_date else None,
    }
        
    publish_permissions_updated(
        auth_user_id,
        str(purchased.id),
        perms_payload,
        purchased_plan_info,
        templates=templates,
        dynamic_capabilities=dynamic_caps
    )
    print("Published successfully.")
else:
    print("Not found.")
