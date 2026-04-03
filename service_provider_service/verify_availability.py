
import os
import django
import sys
from datetime import datetime

# Setup Django environment
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ServiceProvider, ProviderAvailability
from rest_framework.test import APIRequestFactory
from service_provider.views_availability import AvailabilityViewSet

def test_availability(provider_id, label, employee_id=None):
    factory = APIRequestFactory()
    view = AvailabilityViewSet.as_view({'get': 'available_slots'})
    
    # April 6, 2026 is a Monday
    params = {'date': '2026-04-06'}
    if employee_id:
        params['employee_id'] = employee_id
        
    request = factory.get('/', params)
    response = view(request, provider_id=provider_id)
    
    print(f"\n--- {label} ---")
    print(f"Provider: {provider_id} | Employee Param: {employee_id}")
    print(f"Response Status: {response.status_code}")
    print(f"Slots: {response.data.get('slots', [])}")

# Murali (INDIV)
MURALI_ID = "24b49d84-cdf4-4763-b8eb-f1ddae1fa748"
VIRTUAL_EMP_ID = f"ind-{MURALI_ID}"

# Test calling with a standard provider_id (individual mode)
test_availability(MURALI_ID, "MURALI (STANDARD INDIV CALL)")
# Test calling with the NEW Virtual Employee ID prefix
test_availability(MURALI_ID, "MURALI (VIRTUAL EMP CALL)", employee_id=VIRTUAL_EMP_ID)
