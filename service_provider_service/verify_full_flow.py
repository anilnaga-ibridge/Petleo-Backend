import os
import sys
import django
import json
# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser
from provider_dynamic_fields.views import ProviderCategoryViewSet, ProviderPricingViewSet

# Constants
AUTH_USER_ID = "7470623a-ee4b-4922-99f5-3ce2f17171d7" # Naga Anil
SERVICE_ID = "711fac84-16dc-4252-b7e3-6afb7ee57c71" # Grooming (or whatever service was purchased)

def verify_api():
    print(f"--- Verifying API Response for User {AUTH_USER_ID} and Service {SERVICE_ID} ---")
    
    try:
        user = VerifiedUser.objects.get(auth_user_id=AUTH_USER_ID)
        print(f"User Found: {user.full_name}")
    except VerifiedUser.DoesNotExist:
        print("User NOT found!")
        return

    factory = APIRequestFactory()
    
    # 1. Verify Categories & Facilities
    print("\n--- Categories API ---")
    view = ProviderCategoryViewSet.as_view({'get': 'list'})
    request = factory.get(f'/api/provider/categories/?service={SERVICE_ID}')
    class MockUser:
        id = AUTH_USER_ID
        is_authenticated = True
    
    force_authenticate(request, user=MockUser())
    request.user = MockUser()
    
    response = view(request)
    if response.status_code == 200:
        data = response.data
        print(f"Total Categories: {len(data)}")
        for cat in data:
            print(f" [Category] {cat['name']} (Template: {cat.get('is_template')})")
            print(f"    - Can View: {cat.get('can_view')}")
            facs = cat.get('facilities', [])
            print(f"    - Facilities: {len(facs)}")
            for f in facs:
                print(f"      - {f['name']} (Price: {f.get('price')})")
    else:
        print(f"Error: {response.status_code} - {response.data}")

    # 2. Verify Pricing
    print("\n--- Pricing API ---")
    view_pricing = ProviderPricingViewSet.as_view({'get': 'list'})
    request_p = factory.get(f'/api/provider/pricing/?service={SERVICE_ID}')
    force_authenticate(request_p, user=MockUser())
    request_p.user = MockUser()
    
    response_p = view_pricing(request_p)
    if response_p.status_code == 200:
        data_p = response_p.data
        print(f"Total Pricing Rules: {len(data_p)}")
        for p in data_p:
            print(f" [Price] {p['price']} for {p.get('category_name')} / {p.get('facility_name')}")
            print(f"    - Can View: {p.get('can_view')}")
    else:
        print(f"Error: {response_p.status_code} - {response_p.data}")

if __name__ == "__main__":
    verify_api()
