
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from provider_dynamic_fields.views_combined import ProviderProfileView
from service_provider.models import VerifiedUser

def test_profile_endpoint():
    # 1. Get User
    try:
        user = VerifiedUser.objects.get(phone_number='8522047175')
        print(f"Testing for User: {user.email} (ID: {user.auth_user_id})")
    except VerifiedUser.DoesNotExist:
        print("User not found!")
        return

    # 2. Create Request
    factory = APIRequestFactory()
    url = f'/api/provider/profile/?user={user.auth_user_id}&target=individual'
    request = factory.get(url)
    
    # 3. Call View
    view = ProviderProfileView.as_view()
    response = view(request)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success!")
        data = response.data
        print(f"Fields Count: {len(data.get('fields', []))}")
        print(f"Documents Count: {len(data.get('requested_documents', []))}")
    else:
        print("Failed!")
        print(response.data)

if __name__ == "__main__":
    test_profile_endpoint()
