import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import Plan

print(f"{'ID':<36} | {'Title':<20} | {'Price':<10}")
print("-" * 70)
for plan in Plan.objects.all():
    print(f"{str(plan.id):<36} | {plan.title:<20} | {plan.price:<10}")
