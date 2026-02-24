import os
import json
import django
from django.core.files.uploadedfile import SimpleUploadedFile
# Setup Django for Service Provider Service
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser as SP_VerifiedUser
from service_provider.views import ServiceProviderProfileView

def test_superadmin_sync(email):
    # 1. Update in Service Provider Service
    try:
        user = SP_VerifiedUser.objects.get(email=email)
        factory = APIRequestFactory()
        
        print(f"\n--- Updating SuperAdmin Profile in SP Service: {email} ---")
        avatar_content = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        avatar_file = SimpleUploadedFile('sa_avatar.gif', avatar_content, content_type='image/gif')
        
        data = {
            'auth_user_id': str(user.auth_user_id),
            'avatar': avatar_file,
            'fields': '[]'
        }
        
        request = factory.post('/api/provider/profile/', data, format='multipart')
        force_authenticate(request, user=user)
        response = ServiceProviderProfileView.as_view()(request)
        
        if response.status_code == 200:
            new_avatar_url = response.data.get('user_profile', {}).get('avatar')
            print(f"✅ SP Update Success. New Avatar URL: {new_avatar_url}")
            
            # Now wait a bit for Kafka and check Super Admin Service
            print("⏳ Waiting for Kafka sync (5s)...")
            import time
            time.sleep(5)
            
            # Switch to Super Admin Service DB
            os.environ["DJANGO_SETTINGS_MODULE"] = "super_admin_service.settings"
            # We need to re-setup or import models directly with the new settings
            # But in the same process it might be tricky due to django caching.
            # So we'll just use a sub-process or raw SQL for the check.
            
            print(f"\n--- Checking SuperAdmin Service DB for {email} ---")
            import subprocess
            check_cmd = f"cd '/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service' && ./venv/bin/python3 -c \"import os; import django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings'); django.setup(); from admin_core.models import VerifiedUser; user = VerifiedUser.objects.get(email='{email}'); print(f'Avatar URL in SA Service: {{user.avatar_url}}')\""
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                 print(f"Error checking SA Service: {result.stderr}")
        else:
            print(f"❌ SP Update Failed: {response.data}")

    except Exception as e:
        print(f"Error testing sync: {e}")

if __name__ == "__main__":
    test_superadmin_sync("admin@gmail.com")
