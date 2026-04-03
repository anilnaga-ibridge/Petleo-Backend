
import os
import django
import uuid
import sys

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"

# --- 1. Auth Service ---
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service', 'auth_service')))
    os.environ["DJANGO_SETTINGS_MODULE"] = "auth_service.settings"
    django.setup()
    from users.models import User
    user = User.objects.get(id=uuid.UUID(auth_user_id))
    user.avatar_url = None
    user.save()
    print("✅ Auth Service: Avatar cleared.")
except Exception as e:
    print(f"❌ Auth Service Error: {e}")

# --- 2. Super Admin Service ---
try:
    from importlib import reload
    import sys
    # Clear previous django setup
    for key in list(sys.modules.keys()):
        if key.startswith('django'):
            del sys.modules[key]
    
    os.environ["DJANGO_SETTINGS_MODULE"] = "super_admin_service.settings"
    import django
    django.setup()
    from admin_core.models import VerifiedUser
    vuser = VerifiedUser.objects.get(auth_user_id=auth_user_id)
    vuser.avatar_url = None
    vuser.save()
    print("✅ Super Admin Service: Avatar cleared.")
except Exception as e:
    print(f"❌ Super Admin Service Error: {e}")

# --- 3. Service Provider Service ---
try:
    from importlib import reload
    import sys
    for key in list(sys.modules.keys()):
        if key.startswith('django'):
            del sys.modules[key]

    os.environ["DJANGO_SETTINGS_MODULE"] = "service_provider_service.settings"
    import django
    django.setup()
    from service_provider.models import VerifiedUser as SP_VerifiedUser, ServiceProvider
    
    vuser_sp = SP_VerifiedUser.objects.get(auth_user_id=auth_user_id)
    vuser_sp.avatar_url = None
    vuser_sp.save()
    
    profile = ServiceProvider.objects.get(verified_user__auth_user_id=auth_user_id)
    profile.avatar = None
    profile.save()
    print("✅ Service Provider Service: Avatar cleared.")
except Exception as e:
    print(f"❌ Service Provider Service Error: {e}")
