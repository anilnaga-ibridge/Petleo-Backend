import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import BillingCycleConfig, Plan

print("Billing Cycles:")
for bc in BillingCycleConfig.objects.all():
    print(f"Code: {bc.code}, Active: {bc.is_active}")

print("\nPlans:")
for p in Plan.objects.all():
    print(f"ID: {p.id}, Title: {p.title}, Billing Cycle: {p.billing_cycle}")
