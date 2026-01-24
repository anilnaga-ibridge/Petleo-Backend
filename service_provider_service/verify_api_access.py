
import os
import django
import sys
from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.views import MyAccessView

def run():
    print("\n🌐 --- VERIFICATION: CHECKING API ACCESS (/permissions/my-access/) ---")
    
    try:
        with open("../super_admin_service/verify_ids.txt", "r") as f:
            ids = f.read().strip().split("\n")
            if len(ids) < 2: return
            user_a_id, user_b_id = ids[0].strip(), ids[1].strip()
    except FileNotFoundError:
        return

    factory = APIRequestFactory()
    view = MyAccessView.as_view()

    # USER A
    check_user(factory, view, user_a_id, "User A", expect_module="gold-board", forbid_module="silver-board")
    
    # USER B
    check_user(factory, view, user_b_id, "User B", expect_module="silver-board", forbid_module="gold-board")

def check_user(factory, view, auth_id, label, expect_module, forbid_module):
    print(f"\n🔍 Checking API for {label}...")
    user = VerifiedUser.objects.get(auth_user_id=auth_id)
    
    # Mock Request
    request = factory.get('/api/provider/permissions/my-access/')
    
    # We need to monkeypatch request.user or use a mock authentication class depending on how View identifies user.
    # The view likely uses request.user.verified_user or auth_user_id from token.
    # Assuming standard DRF + custom auth middleware logic.
    # For unit test, we can force authenticated user if the View uses request.user.
    
    # HACK: If the view relies on auth_user_id in request.user, we need a mock user.
    class MockUser:
        is_authenticated = True
        auth_user_id = auth_id
        # Add other fields if needed by MyAccessView logic
        
    request.user = MockUser()
    
    response = view(request)
    data = response.data
    
    modules = data.get('modules', [])
    routes = [m['route'] for m in modules]
    
    print(f"   > Modules Returned: {routes}")
    
    if expect_module in routes:
        print(f"   ✅ Correctly sees {expect_module}")
    else:
        print(f"   ❌ MISSING {expect_module}")
        
    if forbid_module in routes:
        print(f"   ❌ ERROR: Sees forbidden {forbid_module}")
    else:
        print(f"   ✅ Correctly blocked from {forbid_module}")

if __name__ == "__main__":
    run()
