import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

users = VerifiedUser.objects.all()
print(f"{'FullName':<20} | {'Auth User ID':<36} | {'Role':<15}")
print("-" * 100)
for u in users:
    print(f"{u.full_name:<20} | {str(u.auth_user_id):<36} | {getattr(u, 'role', 'N/A'):<15}")
