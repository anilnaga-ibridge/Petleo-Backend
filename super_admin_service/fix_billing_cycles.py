import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import Plan

for plan in Plan.objects.all():
    if plan.billing_cycle and plan.billing_cycle != plan.billing_cycle.upper():
        print(f"Fixing plan {plan.id}: {plan.billing_cycle} -> {plan.billing_cycle.upper()}")
        plan.billing_cycle = plan.billing_cycle.upper()
        plan.save()
