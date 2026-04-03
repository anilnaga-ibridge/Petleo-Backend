
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ServiceProvider

try:
    profiles = ServiceProvider.objects.all().order_by('-updated_at')[:5]
    for p in profiles:
        print(f"ID: {p.id} | Auth ID: {p.verified_user.auth_user_id} | Name: {p.verified_user.full_name} | Updated: {p.updated_at} | Avatar: {p.avatar}")
except Exception as e:
    print(f"Error: {e}")
