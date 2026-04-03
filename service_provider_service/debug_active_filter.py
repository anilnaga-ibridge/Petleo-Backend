import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider
from service_provider.services import ProviderService
from service_provider.serializers import ActiveProviderDTO
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

def test_active_endpoint():
    print("--- Detailed Marketplace Logic Test ---")
    
    # 1. Direct Model Filter
    qs = ServiceProvider.objects.filter(
        profile_status='active',
        is_fully_verified=True,
        verified_user__subscription__is_active=True
    )
    print(f"Base count: {qs.count()}")
    for p in qs:
        print(f" - ID: {p.id}, Role: {repr(p.verified_user.role)}, Name: {p.verified_user.full_name}")

    # 2. Exclude Filter
    qs_excluded = qs.exclude(verified_user__role__iexact='superadmin')
    print(f"Count after exclude: {qs_excluded.count()}")
    for p in qs_excluded:
        print(f" - ID: {p.id}, Role: {repr(p.verified_user.role)}, Name: {p.verified_user.full_name}")

    # 3. Via Service
    providers = ProviderService.list_active_providers()
    print(f"ProviderService count: {providers.count()}")

if __name__ == "__main__":
    test_active_endpoint()
