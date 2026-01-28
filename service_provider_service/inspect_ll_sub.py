
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_cart.models import PurchasedPlan
# We need to reach out to Super Admin DB for Plan definitions, 
# but simpler to check what PurchasedPlan says vs what User has.

user = VerifiedUser.objects.filter(auth_user_id="076875b0-ca6b-4d96-a5a5-36f29e8cd976").first()
if not user:
    print("User ll@gmail.com not found")
    sys.exit(1)

sub = PurchasedPlan.objects.filter(verified_user=user, is_active=True).first()
if sub:
    print(f"Active Subscription: {sub.plan_title} (ID: {sub.plan_id})")
else:
    print("No active subscription found.")

# We know from previous steps 'll' has 0 caps (except the one we added).
# We should list what SHOULD be there.
# This requires querying Super Admin Service or just assuming Gold Plan structure mentioned by user.
