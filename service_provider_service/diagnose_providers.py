import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess

print("--- Provider Diagnostic ---")
providers = ServiceProvider.objects.all()
print(f"Total Providers: {providers.count()}")

active_providers = ServiceProvider.objects.filter(
    profile_status='active',
    is_fully_verified=True,
    verified_user__subscription__is_active=True
).distinct()
print(f"Active Marketable Providers: {active_providers.count()}")

if active_providers.count() == 0:
    print("\nDetailed Status of All Providers:")
    for p in providers:
        user = p.verified_user
        sub_active = user.subscription.filter(is_active=True).exists()
        print(f"- ID: {p.id}")
        print(f"  Name: {user.full_name} ({user.email})")
        print(f"  Status: {p.profile_status}")
        print(f"  Verified: {p.is_fully_verified}")
        print(f"  Subscription Active: {sub_active}")
        print("-" * 20)
