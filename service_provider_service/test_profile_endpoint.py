import os
import django
import sys
import json
from django.test import RequestFactory

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS += ['testserver']

from provider_dynamic_fields.views_combined import ProviderProfileView
from service_provider.models import VerifiedUser

def test_api():
    user_id = "0862728b-6a0b-404b-94cd-4d13e5a1bd9b"
    print(f"🚀 Testing Profile API for User ID: {user_id}")
    
    factory = RequestFactory()
    
    # Test for 'employee' target
    request = factory.get(f'/api/provider/profile/?user={user_id}&target=employee')
    
    view = ProviderProfileView.as_view()
    response = view(request)
    
    print(f"📊 Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.data
        print(f"✅ Fields Returned: {len(data.get('fields', []))}")
        for f in data.get('fields', []):
            print(f"   - {f['label']} ({f['name']}): {f['value']}")
    else:
        print("❌ Error Response:")
        print(response.data)

    # Test WITHOUT target (default logic)
    print("\n🚀 Testing Profile API WITHOUT target (defaults)...")
    request = factory.get(f'/api/provider/profile/?user={user_id}')
    response = view(request)
    print(f"📊 Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.data
        print(f"✅ Fields Returned: {len(data.get('fields', []))}")
        for f in data.get('fields', []):
            print(f"   - {f['label']} ({f['name']}): {f['value']}")
    else:
        print("❌ Error Response:")
        print(response.data)

if __name__ == "__main__":
    test_api()
