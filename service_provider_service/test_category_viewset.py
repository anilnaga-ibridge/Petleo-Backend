import os
import django
import sys
import json

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
from django.utils import timezone
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from provider_dynamic_fields.views import ProviderCategoryViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

def test_category_viewset():
    emp_email = "eswar@gmail.com"
    print(f"--- Testing ProviderCategoryViewSet for {emp_email} ---")
    
    try:
        user = VerifiedUser.objects.get(email=emp_email)
        factory = APIRequestFactory()
        # Simulate GET /api/provider/categories/?service=711fac84-16dc-4252-b7e3-6afb7ee57c71
        request = factory.get('/api/provider/categories/', {'service': '711fac84-16dc-4252-b7e3-6afb7ee57c71'})
        force_authenticate(request, user=user)
        
        view = ProviderCategoryViewSet.as_view({'get': 'list'})
        response = view(request)
        
        print(f"Status Code: {response.status_code}")
        print("Response Data:")
        class UUIDEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (timezone.datetime,)):
                    return obj.isoformat()
                import uuid
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                return super().default(obj)

        print(json.dumps(response.data, indent=2, cls=UUIDEncoder))
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_category_viewset()
