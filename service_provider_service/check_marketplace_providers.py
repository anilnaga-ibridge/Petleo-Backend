import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider
from django.utils import timezone

def check_providers():
    print(f"\n{'='*100}")
    print(f"{'PROVIDER MARKETPLACE STATUS CHECK':^100}")
    print(f"{'='*100}\n")
    
    providers = ServiceProvider.objects.all()
    print(f"Total Providers in DB: {providers.count()}\n")
    
    for p in providers:
        user = p.verified_user
        full_name = user.full_name if user else "No User"
        email = user.email if user else "No Email"
        
        # Check Filters
        status_ok = p.profile_status == 'active'
        verified_ok = p.is_fully_verified
        
        # Subscription Check (using the same logic as repository)
        # Note: verified_user__subscription__is_active=True
        # Let's check the related name or field
        has_sub = False
        sub_active = False
        try:
             # Checking related set for ProviderSubscription
             subs = user.subscription.all()
             has_sub = subs.exists()
             sub_active = subs.filter(is_active=True).exists()
        except AttributeError:
             # Maybe the related name is different
             print(f"DEBUG: Could not find 'subscription' on user {email}")
        
        print(f"🏥 Provider: {full_name} ({email})")
        print(f"   ├─ ID: {p.id}")
        print(f"   ├─ Status: {p.profile_status} [{'✅' if status_ok else '❌'}]")
        print(f"   ├─ Verified: {p.is_fully_verified} [{'✅' if verified_ok else '❌'}]")
        print(f"   ├─ Has Subscription: {has_sub}")
        print(f"   └─ Sub Active: {sub_active} [{'✅' if sub_active else '❌'}]")
        
        if status_ok and verified_ok and sub_active:
            print(f"   🌟 SHOULD BE VISIBLE")
        else:
            reasons = []
            if not status_ok: reasons.append("Status not 'active'")
            if not verified_ok: reasons.append("Not 'fully verified'")
            if not sub_active: reasons.append("No active 'ProviderSubscription'")
            print(f"   ⚠️ HIDDEN: {', '.join(reasons)}")
        print("-" * 50)

if __name__ == "__main__":
    check_providers()
