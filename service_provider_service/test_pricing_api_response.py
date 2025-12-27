import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser
from provider_dynamic_fields.views import ProviderPricingViewSet
from provider_dynamic_fields.models import ProviderCapabilityAccess

def test_api_response():
    email = "nagaanil29@gmail.com"
    try:
        user = VerifiedUser.objects.get(email=email)
    except VerifiedUser.DoesNotExist:
        print(f"User {email} not found")
        return

    # Mock User for authentication
    class MockUser:
        def __init__(self, id):
            self.id = id
            self.is_authenticated = True
            self.username = "mockuser"
    
    auth_user = MockUser(user.auth_user_id)
    print(f"Authenticating with Mock User ID: {auth_user.id}")

    # Loop through all permissions
    perms = ProviderCapabilityAccess.objects.filter(user=user)
    print(f"Found {perms.count()} permissions")
    
    factory = APIRequestFactory()
    view = ProviderPricingViewSet.as_view({'get': 'list'})

    for perm in perms:
        service_id = perm.service_id
        if not service_id: continue
            
        print(f"\n--- Testing Service ID: {service_id} ---")
        request = factory.get(f'/api/provider/pricing/?service={service_id}')
        force_authenticate(request, user=auth_user)
        
        response = view(request)
        if response.status_code == 200:
            data = response.data
            results = data['results'] if isinstance(data, dict) and 'results' in data else data
            
            print(f"Found {len(results)} pricing rules")
            for item in results:
                is_tmpl = item.get('is_template')
                can_edit = item.get('can_edit')
                print(f"ID: {item.get('id')} | Tmpl: {is_tmpl} | Edit: {can_edit}")
                
                if is_tmpl and not can_edit:
                    print("  !!! PROBLEM: Template with Edit=False !!!")
                    print(f"  Cat: {item.get('category_id')} | Fac: {item.get('facility')}")

if __name__ == "__main__":
    test_api_response()
