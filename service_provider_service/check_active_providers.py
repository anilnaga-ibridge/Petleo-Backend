
import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ['DJANGO_SETTINGS_MODULE'] = 'service_provider_service.settings'
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser, ProviderSubscription
from provider_cart.models import PurchasedPlan

def check_providers():
    print("🔍 Checking Service Providers...")
    providers = ServiceProvider.objects.all()
    print(f"Total Providers: {providers.count()}")
    
    for p in providers:
        user = p.verified_user
        print(f"\n--- Provider: {user.full_name} ({user.email}) ---")
        print(f"  Role: {user.role}")
        print(f"  Status: {p.profile_status}")
        print(f"  Fully Verified: {p.is_fully_verified}")
        
        # Check Purchased Plans
        purchased = PurchasedPlan.objects.filter(verified_user=user)
        print(f"  Purchased Plans: {purchased.count()}")
        for pp in purchased:
            print(f"    - {pp.plan_title} (Active: {pp.is_active}, End: {pp.end_date})")
            
        # Check Provider Subscriptions
        subs = ProviderSubscription.objects.filter(verified_user=user)
        print(f"  Provider Subscriptions: {subs.count()}")
        for sub in subs:
            print(f"    - {sub.plan_id} (Active: {sub.is_active}, End: {sub.end_date})")
            
    print("\n🔍 Checking Repository Logic Output...")
    from service_provider.repositories import ProviderRepository
    active = ProviderRepository.get_active_providers_for_marketplace()
    print(f"Active Providers found by Repository: {active.count()}")
    for a in active:
        print(f"  - {a.verified_user.full_name}")

if __name__ == "__main__":
    check_providers()
