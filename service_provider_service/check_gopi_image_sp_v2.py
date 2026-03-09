
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider

auth_id = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"

print(f"--- Checking Service Provider Service for {auth_id} ---")
sp = ServiceProvider.objects.filter(verified_user__auth_user_id=auth_id).first()
if sp:
    print(f"ServiceProvider found for {sp.verified_user.full_name}")
    print(f"Avatar: {sp.avatar}")
    if sp.avatar:
        print(f"Avatar Path: {sp.avatar.path}")
        if os.path.exists(sp.avatar.path):
            print("File exists on disk.")
        else:
            print("File does NOT exist on disk.")
else:
    print("ServiceProvider not found.")
