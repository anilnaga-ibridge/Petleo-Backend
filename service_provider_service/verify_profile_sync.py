import os
import django
import json
import requests

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import LocalFieldDefinition, ProviderFieldValue

def test_sync():
    # 1. Find or create a test user
    # auth_user_id = "00000000-0000-0000-0000-000000000001"
    # verified, _ = VerifiedUser.objects.get_or_create(auth_user_id=auth_user_id, defaults={"full_name": "Test User"})
    
    # Let's find an existing user to avoid complications with Auth Service relations
    verified = VerifiedUser.objects.first()
    if not verified:
        print("No users found in DB")
        return
    
    auth_user_id = str(verified.auth_user_id)
    print(f"Testing with User: {verified.full_name} ({auth_user_id})")
    
    # 2. Find or create name fields
    target = getattr(verified, "provider_type", "individual")
    first_name_def, _ = LocalFieldDefinition.objects.get_or_create(
        name="first_name", 
        target=target,
        defaults={"label": "First Name", "field_type": "text"}
    )
    last_name_def, _ = LocalFieldDefinition.objects.get_or_create(
        name="last_name", 
        target=target,
        defaults={"label": "Last Name", "field_type": "text"}
    )
    
    # 3. Simulate submission
    test_first = "Antigravity"
    test_last = "AI"
    
    fields_payload = [
        {"field_id": str(first_name_def.id), "value": test_first},
        {"field_id": str(last_name_def.id), "value": test_last},
    ]
    
    # We'll use the combined profile view logic directly for testing or just mock the request
    # Since we want to test the view logic, we'll hit the API if it's running, 
    # but for speed and reliability in this env, we'll check the logic via a direct call if possible.
    # Actually, let's just use the logic from views_combined.py (simulated)
    
    print(f"Simulating submission of: {test_first} {test_last}")
    
    from provider_dynamic_fields.views_combined import ProviderProfileView
    from rest_framework.test import APIRequestFactory
    
    factory = APIRequestFactory()
    data = {
        "fields": json.dumps(fields_payload),
        "user": auth_user_id
    }
    request = factory.post(f'/api/provider/profile/?user={auth_user_id}', data)
    
    view = ProviderProfileView.as_view()
    response = view(request)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    # 4. Verify DB
    verified.refresh_from_db()
    print(f"Updated Full Name: {verified.full_name}")
    
    if verified.full_name == f"{test_first} {test_last}":
        print("✅ SUCCESS: Name correctly synced to VerifiedUser")
    else:
        print("❌ FAILURE: Name NOT synced correctly")

if __name__ == "__main__":
    test_sync()
