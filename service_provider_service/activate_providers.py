import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, ProviderSubscription, VerifiedUser

def activate_all():
    print("--- Activating All Providers ---")
    providers = ServiceProvider.objects.all()
    
    for p in providers:
        user = p.verified_user
        print(f"Activating {user.full_name} ({user.email})...")
        
        # 1. Update ServiceProvider status
        p.profile_status = 'active'
        p.is_fully_verified = True
        p.save()
        
        # 2. Ensure active subscription
        sub, created = ProviderSubscription.objects.get_or_create(
            verified_user=user,
            defaults={
                'plan_id': 'MOCK_PLAN',
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=365),
                'is_active': True
            }
        )
        if not created and not sub.is_active:
            sub.is_active = True
            sub.save()
            
        print(f"  - Status set to 'active'")
        print(f"  - is_fully_verified set to True")
        print(f"  - Subscription ensured active")

    print(f"\nSuccessfully processed {providers.count()} providers.")

if __name__ == "__main__":
    activate_all()
