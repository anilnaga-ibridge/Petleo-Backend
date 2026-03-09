import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee

print(f"VerifiedUser count: {VerifiedUser.objects.count()}")
for user in VerifiedUser.objects.all()[:10]:
    print(f"User: {user.email}, authID: {user.auth_user_id}, role: {user.role}")

print(f"\nOrganizationEmployee count: {OrganizationEmployee.objects.count()}")
for emp in OrganizationEmployee.objects.all():
    print(f"Emp: {emp.full_name}, authID: {emp.auth_user_id}")
