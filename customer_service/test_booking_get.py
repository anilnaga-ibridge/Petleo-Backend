import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.renderers import JSONRenderer
from bookings.views import BookingViewSet
from customers.models import PetOwnerProfile

def test_get():
    print("--- Testing Booking GET ---")
    try:
        p = PetOwnerProfile.objects.get(id='f763db14-d12f-4993-87de-73e523674041')
        factory = APIRequestFactory()
        
        # Test 1: Pet Owner Mode
        print("\n--- Sub-test: Pet Owner Mode ---")
        provider_id = '176596b2-8267-4ddc-a067-86dd9a55117e'
        request = factory.get(f'/api/pet-owner/bookings/bookings/?provider_id={provider_id}')
        force_authenticate(request, user=p)
        request.auth = {'role': 'pet_owner'}
        
        view = BookingViewSet.as_view({'get': 'list'})
        response = view(request)
        response.render()
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        print(f"Status: {response.status_code}, Count: {len(data)}")

        # Test 2: Provider Mode (Custom Role: Spa)
        print("\n--- Sub-test: Provider Mode (Role: Spa) ---")
        request = factory.get('/api/pet-owner/bookings/bookings/')
        # Use provider_id from the logs
        provider_id = '176596b2-8267-4ddc-a067-86dd9a55117e'
        
        # Mock a provider user
        class ProviderUser:
            id = provider_id
            is_authenticated = True
            is_provider = True
            def __str__(self): return f"Provider {provider_id}"
        
        force_authenticate(request, user=ProviderUser())
        request.auth = {'role': 'Spa', 'user_id': provider_id}
        
        view = BookingViewSet.as_view({'get': 'list'})
        response = view(request)
        response.render()
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        print(f"Status: {response.status_code}, Count: {len(data)}")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get()
