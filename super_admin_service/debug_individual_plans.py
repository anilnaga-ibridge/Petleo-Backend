import os
import django
from django.db.models import Count

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import PurchasedPlan, Plan
from django.contrib.auth import get_user_model

User = get_user_model()

print("--- Individual Providers with Multiple Plans ---")
# Group by user and count purchased plans
user_plan_counts = PurchasedPlan.objects.values('user').annotate(plan_count=Count('id')).filter(plan_count__gte=2)

for entry in user_plan_counts:
    user_id = entry['user']
    count = entry['plan_count']
    try:
        user = User.objects.get(id=user_id)
        if user.user_role == 'individual':
            print(f"\nUser: {user.email} (ID: {user.id}) - Plans: {count}")
            purchases = PurchasedPlan.objects.filter(user=user)
            all_services = set()
            for pp in purchases:
                print(f"  - Plan: {pp.plan.title}")
                # Check capabilities of the plan
                for cap in pp.plan.capabilities.all():
                    if cap.service:
                        all_services.add(f"{cap.service.display_name} ({cap.service.id})")
            
            print(f"  Expected Services ({len(all_services)}):")
            for s in all_services:
                print(f"    - {s}")
    except User.DoesNotExist:
        print(f"User ID {user_id} not found")
