import os
import json
import django

# Setup Django FIRST
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

# Now imports
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate
from django.utils import timezone

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee
from service_provider.views import ServiceProviderProfileView
from provider_dynamic_fields.models import LocalFieldDefinition

def test_unified_profile(email):
    try:
        user = VerifiedUser.objects.get(email=email)
        factory = APIRequestFactory()
        
        print(f"\n--- Testing Unified Profile GET: {email} ---")
        request = factory.get('/api/provider/profile/', {'user': str(user.auth_user_id)})
        force_authenticate(request, user=user)
        view = ServiceProviderProfileView.as_view()
        response = view(request)
        
        if response.status_code == 200:
            print("✅ GET Success")
            print(f"Fields count: {len(response.data.get('fields', []))}")
            if 'fields' in response.data and response.data['fields']:
                 # Find profile_image field to display its value
                 pi_field = next((f for f in response.data['fields'] if f['name'] == 'profile_image'), response.data['fields'][0])
                 print(f"Profile Image Field: {pi_field['label']} = {pi_field['value']} (ID: {pi_field['id']})")
        else:
            print(f"❌ GET Failed: {response.status_code}")
            print(response.data)
            return

        # Test POST with dynamic profile_image
        print(f"\n--- Testing Unified Profile POST (Avatar + Dynamic Field): {email} ---")
        
        # Find the profile_image field ID
        profile_image_field = LocalFieldDefinition.objects.filter(name="profile_image", target='organization' if user.role == 'organization' else 'individual').first()
        
        avatar_content = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        
        # 1. Main Avatar
        avatar_file = SimpleUploadedFile('main_avatar.gif', avatar_content, content_type='image/gif')
        
        data = {
            'auth_user_id': str(user.auth_user_id),
            'avatar': avatar_file,
            'fields': json.dumps([
                {'field_id': str(profile_image_field.id), 'value': None} if profile_image_field else {}
            ])
        }
        
        # 2. Dynamic Field Avatar (if exists)
        if profile_image_field:
            dynamic_avatar_file = SimpleUploadedFile('dynamic_avatar.gif', avatar_content, content_type='image/gif')
            data[str(profile_image_field.id)] = dynamic_avatar_file
            print(f"Using dynamic field ID: {profile_image_field.id}")

        request = factory.post('/api/provider/profile/', data, format='multipart')
        force_authenticate(request, user=user)
        response = view(request)

        if response.status_code == 200:
            print("✅ POST Success")
            print("Message:", response.data.get('message'))
            print("Avatar URL:", response.data.get('user_profile', {}).get('avatar'))
            
            # Check VerifiedUser.avatar_url
            user.refresh_from_db()
            print(f"VerifiedUser.avatar_url: {user.avatar_url}")
            if user.avatar_url and 'main_avatar' in user.avatar_url or 'dynamic_avatar' in user.avatar_url:
                 print("✅ Sync Verified!")
            else:
                 print("❌ Sync mismatch or not found")
        else:
            print(f"❌ POST Failed: {response.status_code}")
            print(response.data)

    except Exception as e:
        print(f"Error testing {email}: {e}")

if __name__ == "__main__":
    test_unified_profile("raj@gmail.com")
    test_unified_profile("lavanya@gmail.com")
