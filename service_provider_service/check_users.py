
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider

users = VerifiedUser.objects.all()
print(f"Total VerifiedUsers: {users.count()}")
for user in users:
    print(f"User: {user.email} | Name: {user.full_name} | Role: {user.role}")
    provider = ServiceProvider.objects.filter(verified_user=user).first()
    if provider:
        print(f"  Provider Avatar: {provider.avatar.url if provider.avatar else 'None'}")
    else:
        print("  No ServiceProvider profile found.")
