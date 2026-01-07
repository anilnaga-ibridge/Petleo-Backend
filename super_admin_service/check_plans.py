
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import Plan

print(f"{'ID':<36} | {'Title':<30} | {'Subtitle':<30} | {'Target Type':<15}")
print("-" * 120)
for plan in Plan.objects.all():
    print(f"{str(plan.id):<36} | {plan.title:<30} | {plan.subtitle:<30} | {plan.target_type:<15}")
