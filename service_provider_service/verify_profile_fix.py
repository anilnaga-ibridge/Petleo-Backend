
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from service_provider.views import get_my_permissions, ServiceProviderProfileView
from rest_framework.test import APIRequestFactory, force_authenticate
from django.core.files.uploadedfile import SimpleUploadedFile

factory = APIRequestFactory()

def test_user_profile(email):
    try:
        user = VerifiedUser.objects.get(email=email)
        request = factory.get('/api/provider/permissions/')
        force_authenticate(request, user=user)
        response = get_my_permissions(request)
        
        print(f"\n--- Testing User Permissions: {email} ---")
        if response.status_code == 200:
            profile = response.data.get('user_profile', {})
            print(json.dumps(profile, indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(response.data)
    except Exception as e:
        print(f"Error testing permissions for {email}: {e}")

def test_profile_update(email):
    try:
        user = VerifiedUser.objects.get(email=email)
        # Create a valid 1x1 transparent GIF
        avatar_content = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        avatar_file = SimpleUploadedFile('test_avatar.gif', avatar_content, content_type='image/gif')
        
        data = {
            'auth_user_id': str(user.auth_user_id),
            'full_name': f"{user.full_name} Updated",
            'avatar': avatar_file
        }
        
        request = factory.post('/api/provider/profile/', data, format='multipart')
        force_authenticate(request, user=user)
        
        view = ServiceProviderProfileView.as_view()
        response = view(request)

        print(f"\n--- Testing Profile Update: {email} ---")
        if response.status_code == 200:
            print("Response Message:", response.data.get('message'))
            if 'user_profile' in response.data:
                print("✅ user_profile found in response")
                print(json.dumps(response.data['user_profile'], indent=2))
            else:
                print("❌ user_profile NOT found in response")
            
            # Check VerifiedUser.avatar_url
            user.refresh_from_db()
            print(f"VerifiedUser.avatar_url: {user.avatar_url}")
            if user.avatar_url:
                print("✅ VerifiedUser.avatar_url synced")
            else:
                print("❌ VerifiedUser.avatar_url NOT synced")
        else:
            print(f"Error: {response.status_code}")
            print(response.data)
    except Exception as e:
        print(f"Error testing profile update for {email}: {e}")

# Test an organization user
test_user_profile('raj@gmail.com')
test_profile_update('raj@gmail.com')

# Test an employee user
test_user_profile('lavanya@gmail.com')
