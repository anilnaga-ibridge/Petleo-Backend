import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.views import EmployeeViewSet
from service_provider.models import VerifiedUser

def debug_nagaanil_api():
    print("--- Debugging API for nagaanil292 ---")
    
    # 1. Get User
    try:
        user = VerifiedUser.objects.get(email='nagaanil292@gmail.com')
        print(f"User: {user.email}")
    except VerifiedUser.DoesNotExist:
        print("User nagaanil292 not found")
        return
    
    # 2. Create Request
    factory = APIRequestFactory()
    request = factory.get('/api/provider/employees/')
    force_authenticate(request, user=user) 
    
    # 3. Invoke View
    view = EmployeeViewSet.as_view({'get': 'list'})
    
    try:
        response = view(request)
        print(f"Status Code: {response.status_code}")
        
        import json
        data = response.data
        if hasattr(data, 'results'): 
             data = data.results
             
        print(json.dumps(data, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ View Error: {e}")

if __name__ == "__main__":
    debug_nagaanil_api()
