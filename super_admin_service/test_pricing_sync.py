import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from django.contrib.auth import get_user_model
from plans_coupens.models import PurchasedPlan, Plan
from plans_coupens.purchase_publish_wrapper import purchase_plan_and_publish
from plans_coupens.kafka_producer import publish_permissions_updated

User = get_user_model()

def test_pricing_sync():
    email = "auto_7470623a-ee4b-4922-99f5-3ce2f17171d7@central-auth.local"
    try:
        user = User.objects.get(email=email)
        print(f"Found user: {user.email} (ID: {user.id})")
    except User.DoesNotExist:
        print("User not found")
        return

    try:
        plan = Plan.objects.get(title="Platinum")
        print(f"Found plan: {plan.title}")
    except Plan.DoesNotExist:
        print("Plan not found")
        return

    # Delete existing purchase to force re-sync
    PurchasedPlan.objects.filter(user=user, plan=plan).delete()
    print("Deleted existing purchase")

    print("Simulating purchase...")
    # This calls our modified wrapper which should now include pricing
    purchase_plan_and_publish(user, plan)
    print("Purchase simulated and event published.")

if __name__ == "__main__":
    test_pricing_sync()
