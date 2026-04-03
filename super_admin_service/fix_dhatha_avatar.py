
import os
import django
import uuid

# --- 1. Update Auth Service ---
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service', 'auth_service')))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
# We'll use the port 8002 as defined in axios.js for provider service
avatar_url = "http://127.0.0.1:8002/media/provider_profile/5ee51be1-7065-43e0-898a-2dca34dd3820/5323588bde8f48b58d78f4adaeb5c58f-C_hrd8Ke0.png"

try:
    user = User.objects.get(id=uuid.UUID(auth_user_id))
    user.avatar_url = avatar_url
    user.save()
    print(f"✅ Auth Service: Updated avatar for {user.full_name}")
except Exception as e:
    print(f"❌ Auth Service Error: {e}")

# --- 2. Update Super Admin Service ---
# Reset Django to use Super Admin Settings
from importlib import reload
os.environ["DJANGO_SETTINGS_MODULE"] = "super_admin_service.settings"
import django
reload(django)
django.setup()

from admin_core.models import VerifiedUser

try:
    vuser = VerifiedUser.objects.get(auth_user_id=auth_user_id)
    vuser.avatar_url = avatar_url
    vuser.save()
    print(f"✅ Super Admin Service: Updated avatar for {vuser.full_name}")
except Exception as e:
    print(f"❌ Super Admin Service Error: {e}")
