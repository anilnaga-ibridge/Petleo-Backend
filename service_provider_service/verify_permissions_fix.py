import os
import django
import sys
from unittest.mock import MagicMock

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.authentication import TransientUser
from service_provider.views import get_my_permissions, get_my_access
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response

def verify_permissions_transient_user():
    print(f"\n{'='*100}")
    print(f"{'PERMISSIONS TRANSIENT USER VERIFICATION':^100}")
    print(f"{'='*100}\n")
    
    factory = APIRequestFactory()
    user = TransientUser(auth_user_id='test-auth-id', email='test@customer.com', full_name='Test Customer')
    
    # 1. Test get_my_permissions
    print("🔍 Testing get_my_permissions with TransientUser...")
    request = factory.get('/api/provider/permissions/')
    request.user = user
    
    # Bypass the @permission_classes check by calling the underlying function if needed, 
    # but @api_view wraps it. We can call .wrapped_view or just mock the check.
    # Actually, if we call it directly, we might need to mock more.
    
    try:
        # Wrap in a way that bypasses DRF generic checks if possible, or just call the func
        # The function itself is what we want to test.
        # @api_view decorated functions have the original func in .__wrapped__ (in some versions)
        # or we can just hope it works if we mock the auth.
        
        # Another way: call the function directly (it's a decorated function)
        response = get_my_permissions(request._request if hasattr(request, '_request') else request)
        
        if isinstance(response, Response):
            print(f"✅ get_my_permissions response status: {response.status_code}")
            print(f"📊 Response Data: {response.data}")
        else:
            print(f"✅ get_my_permissions returned: {response}")
            
    except Exception as e:
        print(f"❌ get_my_permissions CRASHED: {e}")
        import traceback
        traceback.print_exc()

    # 2. Test get_my_access
    print("\n🔍 Testing get_my_access with TransientUser...")
    request = factory.get('/api/provider/permissions/my-access/')
    request.user = user
    
    try:
        response = get_my_access(request._request if hasattr(request, '_request') else request)
        if isinstance(response, Response):
            print(f"✅ get_my_access response status: {response.status_code}")
            print(f"📊 Response Data: {response.data}")
        else:
             print(f"✅ get_my_access returned: {response}")
    except Exception as e:
        print(f"❌ get_my_access CRASHED: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Permissions verification completed!")

if __name__ == "__main__":
    verify_permissions_transient_user()
