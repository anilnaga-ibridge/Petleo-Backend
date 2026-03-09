import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, ProviderSubscription, AllowedService

def activate_eligible_providers():
    print(f"--- Starting Provider Activation Process ---")
    
    # Logic: Find providers who have an active subscription but are still pending or unverified
    eligible_subs = ProviderSubscription.objects.filter(is_active=True)
    eligible_auth_ids = eligible_subs.values_list('verified_user__auth_user_id', flat=True)
    
    providers_to_activate = ServiceProvider.objects.filter(
        verified_user_id__in=eligible_auth_ids
    ).filter(
        django.db.models.Q(profile_status='pending') | django.db.models.Q(is_fully_verified=False)
    )
    
    count = providers_to_activate.count()
    print(f"Found {count} providers eligible for activation based on subscriptions.")
    
    # We should also check if they have services allowed, as just having a plan without 
    # being assigned any services might result in an empty-looking profile.
    # However, the user specifically noted Gopi g who HAS services.
    
    activated_count = 0
    for p in providers_to_activate:
        name = p.verified_user.full_name or p.verified_user.email or "Unknown"
        svc_count = AllowedService.objects.filter(verified_user=p.verified_user).count()
        
        print(f"Activating {name}...")
        print(f" - Profile Status: {p.profile_status} -> active")
        print(f" - Is Fully Verified: {p.is_fully_verified} -> True")
        print(f" - Services Found: {svc_count}")
        
        p.profile_status = 'active'
        p.is_fully_verified = True
        p.save()
        activated_count += 1
    
    print(f"\nSuccessfully activated {activated_count} providers.")

if __name__ == "__main__":
    activate_eligible_providers()
