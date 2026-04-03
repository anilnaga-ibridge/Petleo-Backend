
import os
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"

try:
    vuser = VerifiedUser.objects.get(auth_user_id=auth_user_id)
    vuser.avatar_url = None
    vuser.save()
    
    profile = ServiceProvider.objects.get(verified_user__auth_user_id=auth_user_id)
    profile.avatar = None
    profile.save()
    print("✅ Service Provider Service: Avatar cleared.")
except Exception as e:
    print(f"❌ Service Provider Service Error: {e}")
