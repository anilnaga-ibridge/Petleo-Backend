
import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription
from provider_cart.models import PurchasedPlan

def sync_subscriptions():
    print("🚀 Starting Subscription Sync from Cart History...")
    
    # Get all purchased plans
    purchased_plans = PurchasedPlan.objects.all()
    print(f"Found {purchased_plans.count()} purchased plans.")
    
    for pp in purchased_plans:
        user = pp.verified_user
        print(f"\nProcessing User: {user.email} | Plan: {pp.plan_title}")
        
        # Check if subscription exists
        sub = ProviderSubscription.objects.filter(
            verified_user=user,
            plan_id=pp.plan_id
        ).first()
        
        if sub:
            print(f"  ✅ Subscription already exists. Active: {sub.is_active}")
            # Optional: Update dates if missing
            if not sub.start_date:
                sub.start_date = pp.start_date
                sub.save()
                print("  Updated start_date")
        else:
            print(f"  ⚠️ Missing Subscription! Creating...")
            
            # Create subscription
            ProviderSubscription.objects.create(
                verified_user=user,
                plan_id=pp.plan_id,
                billing_cycle_id=pp.billing_cycle_id,
                start_date=pp.start_date,
                end_date=pp.end_date,
                is_active=pp.is_active
            )
            print("  ✅ Created ProviderSubscription")

if __name__ == "__main__":
    sync_subscriptions()
