import os
import sys
import django
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from service_provider.views import get_my_permissions
from rest_framework.test import APIRequestFactory
from django.utils import timezone

def simulate():
    email = "nagaanil29@gmail.com"
    try:
        user = VerifiedUser.objects.get(email=email)
        factory = APIRequestFactory()
        request = factory.get('/api/provider/permissions/')
        request.user = user
        
        response = get_my_permissions(request)
        
        print(json.dumps(response.data, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate()
