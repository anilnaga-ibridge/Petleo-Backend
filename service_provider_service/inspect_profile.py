
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ServiceProvider

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"

try:
    profile = ServiceProvider.objects.get(verified_user__auth_user_id=auth_user_id)
    print(f"Profile Found for Auth ID: {auth_user_id}")
    print(f"Avatar: {profile.avatar}")
except ServiceProvider.DoesNotExist:
    print("Profile not found in Service Provider Service.")
except Exception as e:
    print(f"Error: {e}")
