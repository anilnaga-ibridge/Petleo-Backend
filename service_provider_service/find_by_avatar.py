
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ServiceProvider

filename = "provider_avatars/Photo_on_06-02-26_at_5_VHdf6m7.50PM.jpeg"

try:
    profiles = ServiceProvider.objects.filter(avatar=filename)
    if profiles.exists():
        for p in profiles:
            print(f"Found Profile: {p.verified_user.full_name} | Auth ID: {p.verified_user.auth_user_id}")
    else:
        print("Filename not found in any profile.")
except Exception as e:
    print(f"Error: {e}")
