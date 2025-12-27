import os
import django
import sys
from django.conf import settings

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.views import get_my_permissions
from service_provider.models import VerifiedUser

# Mock Auth User wrapper
class MockAuthUser:
    def __init__(self, id):
        self.id = id
        self.is_authenticated = True
        self.is_staff = False
        self.capabilities = None # Will be patched
        self.subscription = None # Will be patched

def debug_permissions_api():
    print("--- Debugging Permissions API ---")
    
    # 1. Get User
    user = VerifiedUser.objects.order_by('-created_at').first()
    print(f"User: {user.email} (Auth ID: {user.auth_user_id})")
    
    # Patch the user object to have 'capabilities' and 'subscription' related managers
    # Since we are using a mock user for force_authenticate, we need to ensure the view can access 
    # user.capabilities and user.subscription.
    # The view uses `request.user`.
    
    # In the real app, request.user is a VerifiedUser (or similar) that has these relations?
    # No, request.user is usually the Auth User.
    # But `get_my_permissions` does: `user = request.user`
    # And then `user.subscription.first()` and `user.capabilities.all()`.
    
    # Wait! `VerifiedUser` has `capabilities` (related_name='capabilities' on ProviderCapabilityAccess?)
    # Let's check the model definition of ProviderCapabilityAccess.
    
    from provider_dynamic_fields.models import ProviderCapabilityAccess
    # ProviderCapabilityAccess has: user = models.ForeignKey(VerifiedUser, related_name="capabilities", ...)
    
    # So `request.user` MUST be a `VerifiedUser` instance for this to work!
    # But DRF `IsAuthenticated` usually sets `request.user` to the Django User (from Auth Service).
    # How does `service_provider_service` map Auth User to VerifiedUser in `request.user`?
    
    # If it uses a custom authentication class, it might replace request.user.
    # If not, `request.user` is the Auth User (which doesn't have .capabilities).
    
    # Let's check `service_provider/views.py` again.
    # It says: `user = request.user`
    # Then: `subscription = user.subscription.first()`
    
    # If `request.user` is the standard Django User (or MockAuthUser), it won't have `.subscription` unless we add it.
    # BUT `VerifiedUser` is the one with the relations.
    
    # HYPOTHESIS: The view expects `request.user` to be `VerifiedUser`.
    # But standard DRF auth (Token/JWT) usually returns the `User` model.
    # Unless there's a middleware or Auth Backend that swaps it.
    
    # Let's try to run the view with `VerifiedUser` as `request.user`.
    
    factory = APIRequestFactory()
    request = factory.get('/api/provider/permissions/')
    force_authenticate(request, user=user) # Pass VerifiedUser as user
    
    try:
        response = get_my_permissions(request)
        print(f"Status Code: {response.status_code}")
        import json
        print(json.dumps(response.data, indent=2, default=str))
    except Exception as e:
        print(f"❌ View Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_permissions_api()
