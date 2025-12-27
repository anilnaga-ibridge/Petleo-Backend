import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser, OrganizationEmployee, ServiceProvider
from service_provider.views import EmployeeViewSet

USER_EMAIL = "nagaanil29@gmail.com"

print(f"🔍 Verifying Employee List for: {USER_EMAIL}")

try:
    user = VerifiedUser.objects.get(email=USER_EMAIL)
    print(f"✅ Found User: {user.full_name} ({user.auth_user_id})")
    
    # Check Provider Profile
    try:
        provider = ServiceProvider.objects.get(verified_user=user)
        print(f"✅ Found ServiceProvider: {provider.id}")
    except ServiceProvider.DoesNotExist:
        print("❌ ServiceProvider NOT FOUND (This should not happen now)")
        sys.exit(1)

    # Simulate API Request
    factory = APIRequestFactory()
    view = EmployeeViewSet.as_view({'get': 'list'})
    
    request = factory.get('/api/provider/employees/')
    force_authenticate(request, user=user)
    
    response = view(request)
    
    print(f"Response Status: {response.status_code}")
    print(f"Employee Count: {len(response.data)}")
    
    for item in response.data:
        print(f" - {item['full_name']} ({item['email']}) | Status: {item['status']}")
        
    # Verify NO organizations are returned
    # OrganizationEmployee model guarantees this, but let's double check fields
    if len(response.data) > 0:
        first_item = response.data[0]
        if 'profile_status' in first_item: # Field unique to ServiceProvider/Organization
            print("❌ ERROR: Response contains Organization fields! (Should be Employee)")
        else:
            print("✅ Response structure looks like Employee data.")

except VerifiedUser.DoesNotExist:
    print(f"❌ User not found: {USER_EMAIL}")
except Exception as e:
    print(f"❌ Error: {e}")
