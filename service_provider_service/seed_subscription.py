
import os
import django
import sys
import uuid
from django.utils import timezone
from datetime import timedelta

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_cart.models import PurchasedPlan

# Basic Plan ID from Super Admin
PLAN_ID = "c426cef1-c72c-45ca-afd0-5b8f2981640b" 
PLAN_TITLE = "Gold Plan"

# Find ll@gmail.com by Auth ID
user = VerifiedUser.objects.filter(auth_user_id="076875b0-ca6b-4d96-a5a5-36f29e8cd976").first()

if not user:
    print("No Organization user found! Seeding failed.")
    sys.exit(1)

print(f"Seeding subscription for User: {user} (ID: {user.auth_user_id})")

# Check existing
if PurchasedPlan.objects.filter(verified_user=user, is_active=True).exists():
    print("User already has an active subscription.")
else:
    PurchasedPlan.objects.create(
        id=uuid.uuid4(),
        verified_user=user,
        plan_id=PLAN_ID,
        plan_title=PLAN_TITLE,
        billing_cycle_id=1, # Integer ID
        billing_cycle_name="MONTHLY",
        price_amount=89.00,
        price_currency="INR",
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True
    )
    print(f"Successfully purchased {PLAN_TITLE} for {user}.")
