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
    print("--- Testing /api/provider/providers/active/ Logic ---")
    factory = APIRequestFactory()
    request = factory.get('/api/provider/providers/active/')
    
    providers = ProviderService.list_active_providers()
    print(f"ProviderService count: {providers.count()}")
    
    serializer = ActiveProviderDTO(providers, many=True, context={'request': Request(request)})
    print(f"Serialized Providers: {len(serializer.data)}")
    
    if len(serializer.data) > 0:
        print("\nSerialized Data Snippet (First Provider):")
        print(json.dumps(serializer.data[0], indent=2))
    else:
        print("\n❌ STILL NO PROVIDERS SERIALIZED!")

if __name__ == "__main__":
    test_active_endpoint()
