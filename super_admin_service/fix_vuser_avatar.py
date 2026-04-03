
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
avatar_url = "http://127.0.0.1:8002/media/provider_profile/5ee51be1-7065-43e0-898a-2dca34dd3820/5323588bde8f48b58d78f4adaeb5c58f-C_hrd8Ke0.png"

try:
    vuser = VerifiedUser.objects.get(auth_user_id=auth_user_id)
    vuser.avatar_url = avatar_url
    vuser.save()
    print(f"✅ Super Admin Service: Updated avatar for {vuser.full_name}")
except Exception as e:
    print(f"❌ Super Admin Service Error: {e}")
