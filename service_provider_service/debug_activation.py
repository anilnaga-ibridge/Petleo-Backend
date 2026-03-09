import os
import django
import sys
from django.db.models import Q

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, ProviderSubscription, VerifiedUser

print("--- Debugging Activation Query ---")

# Step 1: Active Subscriptions
active_subs = ProviderSubscription.objects.filter(is_active=True)
print(f"Active Subscriptions: {active_subs.count()}")
for sub in active_subs:
    # sub.verified_user_id is the PK (id) of VerifiedUser
    vu_pk = sub.verified_user_id
    vu = VerifiedUser.objects.get(id=vu_pk)
    print(f" - Subscription for VU PK: {vu_pk} | VU Auth ID: {vu.auth_user_id} | Name: {vu.full_name}")

# Step 2: ServiceProviders needing activation
pending_provs = ServiceProvider.objects.filter(Q(profile_status='pending') | Q(is_fully_verified=False))
print(f"\nPending/Unverified ServiceProviders: {pending_provs.count()}")
for p in pending_provs:
    # p.verified_user_id is the auth_user_id (because of to_field='auth_user_id')
    print(f" - SP for VU (auth_user_id): {p.verified_user_id} | Name: {p.verified_user.full_name}")

# Step 3: Intersection check
eligible_auth_ids = [VerifiedUser.objects.get(id=sub.verified_user_id).auth_user_id for sub in active_subs]
print(f"\nEligible Auth IDs from subscriptions: {eligible_auth_ids}")

matching_provs = ServiceProvider.objects.filter(
    verified_user_id__in=eligible_auth_ids
).filter(Q(profile_status='pending') | Q(is_fully_verified=False))

print(f"Matching providers found: {matching_provs.count()}")
for p in matching_provs:
    print(f" - READY TO ACTIVATE: {p.verified_user.full_name}")
