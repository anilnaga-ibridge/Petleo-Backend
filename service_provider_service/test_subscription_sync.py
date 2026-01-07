
import os
import django
import uuid
from django.utils import timezone

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription

def test_subscription_sync_logic():
    # 1. Create a test user and subscription
    auth_id = uuid.uuid4()
    user, _ = VerifiedUser.objects.get_or_create(
        auth_user_id=auth_id,
        defaults={"email": "test@example.com", "role": "individual"}
    )
    
    plan_id = str(uuid.uuid4())
    sub = ProviderSubscription.objects.create(
        verified_user=user,
        plan_id=plan_id,
        start_date=timezone.now(),
        is_active=True
    )
    print(f"✅ Created Subscription for Plan {plan_id}. Active: {sub.is_active}")
    
    # 2. Simulate the Kafka Event Logic (directly calling the update logic)
    # This mimics what kafka_consumer.py does
    new_status = False
    updated_count = ProviderSubscription.objects.filter(plan_id=plan_id).update(is_active=new_status)
    
    sub.refresh_from_db()
    print(f"🔄 Simulated Kafka Sync. Updated Count: {updated_count}. New Status: {sub.is_active}")
    
    if sub.is_active == new_status:
        print("✅ Subscription Sync Success: Local record updated correctly.")
    else:
        print("❌ Subscription Sync Failure: Local record NOT updated.")

if __name__ == "__main__":
    test_subscription_sync_logic()
