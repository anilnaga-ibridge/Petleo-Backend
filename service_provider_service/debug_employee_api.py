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

# Mock Auth User wrapper
class MockAuthUser:
    def __init__(self, id):
        self.id = id
        self.is_authenticated = True
        self.is_staff = False

def debug_employee_api():
    print("--- Debugging Employee API ---")
    
    # 1. Get User
    user = VerifiedUser.objects.order_by('-created_at').first()
    print(f"User: {user.email} (Auth ID: {user.auth_user_id})")
    
    # 2. Create Request
    factory = APIRequestFactory()
    request = factory.get('/api/provider/employees/')
    
    # Mock Auth
    # IMPORTANT: The view uses request.user.
    # If VerifiedUserJWTAuthentication is used, request.user is a VerifiedUser.
    # But force_authenticate sets request.user to whatever we pass.
    # So we should pass the VerifiedUser object itself to simulate the real auth class result.
    force_authenticate(request, user=user) 
    
    # 3. Invoke View
    view = EmployeeViewSet.as_view({'get': 'list'})
    
    try:
        response = view(request)
        print(f"Status Code: {response.status_code}")
        
        import json
        # Handle potential list or dict response
        data = response.data
        if hasattr(data, 'results'): # Pagination
             data = data.results
             
        print(json.dumps(data, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ View Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_employee_api()
