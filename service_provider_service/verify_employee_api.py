import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.response import Response

from service_provider.models import VerifiedUser, OrganizationEmployee, ServiceProvider
from service_provider.views import EmployeeViewSet

ORG_OWNER_ID = "ec23848f-dd25-4701-805d-010cbc9e10fc" # rr@gmail.com

print(f"🔍 Verifying Employee API for Org Owner: {ORG_OWNER_ID}")

try:
    user = VerifiedUser.objects.get(auth_user_id=ORG_OWNER_ID)
    factory = APIRequestFactory()
    view = EmployeeViewSet.as_view({'get': 'list'})
    
    request = factory.get('/api/provider/employees/')
    force_authenticate(request, user=user)
    
    response = view(request)
    
    print(f"Response Status: {response.status_code}")
    print("Response Data:")
    for item in response.data:
        print(f" - {item['full_name']} ({item['email']}) | Status: {item['status']}")
        
    if len(response.data) > 0:
        print("✅ API returned data successfully.")
    else:
        print("❌ API returned empty list.")

except Exception as e:
    print(f"❌ Error: {e}")
