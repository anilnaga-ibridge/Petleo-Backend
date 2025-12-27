import os
import django
import sys
from django.conf import settings

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from provider_dynamic_fields.views import ProviderCategoryViewSet
from service_provider.models import VerifiedUser

def debug_api_response():
    print("--- Debugging API Response ---")
    
    # 1. Get User
    user = VerifiedUser.objects.order_by('-created_at').first()
    print(f"User: {user.email}")
    
    # 2. Target Service ID
    service_id = "d0de4652-d2e7-4cab-ae09-05999f365eed"
    
    # 3. Create Request
    factory = APIRequestFactory()
    request = factory.get(f'/api/provider/categories/?service={service_id}')
    mock_user = MockAuthUser(user.auth_user_id)
    force_authenticate(request, user=mock_user) # Mock auth user
    
    # 4. Invoke View
    view = ProviderCategoryViewSet.as_view({'get': 'list'})
    
    try:
        response = view(request)
        print(f"Status Code: {response.status_code}")
        print("Response Data:")
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

# Mock Auth User wrapper since VerifiedUser links to it via ID
class MockAuthUser:
    def __init__(self, id):
        self.id = id
        self.is_authenticated = True
        self.is_staff = False

if __name__ == "__main__":
    # Patch VerifiedUser to return a mock auth user for force_authenticate
    real_user = VerifiedUser.objects.order_by('-created_at').first()
    mock_user = MockAuthUser(real_user.auth_user_id)
    
    # We need to pass mock_user to force_authenticate, but the view expects request.user to be this mock user.
    # However, get_effective_provider_user uses request.user.id.
    # So MockAuthUser needs 'id' attribute which matches auth_user_id.
    
    debug_api_response()
