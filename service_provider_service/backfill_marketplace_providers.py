import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from service_provider.services import ProviderService

def backfill_marketplace_providers():
    print(f"--- Starting Marketplace Provider Backfill ---")
    
    # Logic: Find all verified users who have at least one active purchased plan
    from provider_cart.models import PurchasedPlan
    users_with_plans = VerifiedUser.objects.filter(
        purchased_plans__is_active=True
    ).distinct()
    
    count = users_with_plans.count()
    print(f"Found {count} verified users with active purchased plans.")
    
    activated_count = 0
    for user in users_with_plans:
        print(f"Processing {user.full_name or user.email}...")
        success = ProviderService.activate_provider_profile(user)
        if success:
            print(f" ✅ Activated successfully.")
            activated_count += 1
        else:
            print(f" ❌ Failed to find ServiceProvider profile.")
            
    print(f"\nSuccessfully activated {activated_count} providers for the marketplace.")

if __name__ == "__main__":
    backfill_marketplace_providers()
