import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider
from service_provider.services import ProviderService

def test_active_endpoint():
    print("--- Final Marketplace Logic Test ---")
    
    providers = ProviderService.list_active_providers()
    print(f"ProviderService count: {providers.count()}")
    for p in providers:
        print(f" - ID: {p.id}, Role: {repr(p.verified_user.role)}, Name: {p.verified_user.full_name}")

if __name__ == "__main__":
    test_active_endpoint()
