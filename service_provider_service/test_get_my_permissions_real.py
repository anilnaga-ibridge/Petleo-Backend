import os
import django
import sys
import json
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from service_provider.views import get_my_permissions
from rest_framework.test import APIRequestFactory, force_authenticate

def test_real_view():
    user_email = "eswar@gmail.com" # Change this to the email of the user you want to test
    print(f"--- Testing get_my_permissions for {user_email} ---")
    
    try:
        user = VerifiedUser.objects.get(email=user_email)
        factory = APIRequestFactory()
        request = factory.get('/api/provider/permissions/')
        force_authenticate(request, user=user)
        
        response = get_my_permissions(request)
        print(f"Status Code: {response.status_code}")
        print("Response Data:")
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, timezone.datetime):
                    return obj.isoformat()
                return super().default(obj)

        print(json.dumps(response.data, indent=2, cls=DateTimeEncoder))
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_real_view()
