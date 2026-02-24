import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from service_provider.views import get_my_permissions
from rest_framework.test import APIRequestFactory, force_authenticate

def inspect_json_response(email):
    try:
        user = VerifiedUser.objects.get(email=email)
        factory = APIRequestFactory()
        request = factory.get('/api/provider/permissions/')
        force_authenticate(request, user=user)
        
        response = get_my_permissions(request)
        print(f"\n--- JSON Response for {email} ---")
        print(json.dumps(response.data, indent=2, default=str))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_json_response('nainiv6@gmail.com')
