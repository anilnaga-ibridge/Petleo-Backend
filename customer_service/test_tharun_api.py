import os
import django
import json
import sys
from uuid import UUID
from datetime import datetime, date

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/customer_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from bookings.views import BookingViewSet

def test():
    factory = APIRequestFactory()
    request = factory.get('/api/pet-owner/bookings/bookings/')
    
    class User:
        id = '8ff9669b-aa8b-4c2e-863f-ef5420942319'
        auth_user_id = '8ff9669b-aa8b-4c2e-863f-ef5420942319'
        is_authenticated = True
        is_provider = True
        def __str__(self): return 'Tharun'

    view = BookingViewSet.as_view({'get': 'list'})
    force_authenticate(request, user=User())
    request.auth = {'role': 'Spa', 'user_id': '8ff9669b-aa8b-4c2e-863f-ef5420942319'}
    
    response = view(request)
    response.render()
    
    results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
    
    # Check first result for pet_details
    if results and len(results) > 0:
        booking = results[0]
        print(f"Booking ID: {booking.get('id')}")
        print(f"Pet Details: {booking.get('pet_details')}")
        print(f"Pet Name Proxy: {booking.get('pet_name')}")
    else:
        print("No bookings found for Tharun")

if __name__ == "__main__":
    test()
