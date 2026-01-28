
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_cart.models import PurchasedPlan

print(f"Total Verified Users: {VerifiedUser.objects.count()}")

for user in VerifiedUser.objects.all():
    print(f"User: {user} (Auth ID: {user.auth_user_id})")
    plans = PurchasedPlan.objects.filter(verified_user=user)
    print(f"  Plans: {plans.count()}")
    for p in plans:
        print(f"    - {p.plan_title} (Active: {p.is_active})")
