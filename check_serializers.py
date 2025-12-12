import os
import django
from django.conf import settings

# Setup Django environment
import sys
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from super_admin_service.plans_coupens.serializers import PlanSerializer, BillingCycleSerializer

print("PlanSerializer fields:", list(PlanSerializer().fields.keys()))
print("BillingCycleSerializer fields:", list(BillingCycleSerializer().fields.keys()))
