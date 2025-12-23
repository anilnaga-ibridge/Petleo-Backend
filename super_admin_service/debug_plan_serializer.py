
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import Plan
from plans_coupens.serializers import PlanSerializer
import traceback

def debug_plans():
    print("Fetching all plans...")
    plans = Plan.objects.all()
    print(f"Found {plans.count()} plans.")

    for plan in plans:
        print(f"Serializing Plan ID: {plan.id} - {plan.title}")
        try:
            serializer = PlanSerializer(plan)
            data = serializer.data
            print("✅ Success")
        except Exception as e:
            print(f"❌ Error serializing plan {plan.id}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    debug_plans()
