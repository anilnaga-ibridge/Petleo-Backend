import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider

for emp in OrganizationEmployee.objects.filter(auth_user_id="5c3b54b9-aa99-441d-8598-df3aea0b59fd"):
    print(f"Employee: {emp.full_name}, OrgID (UUID): {emp.organization.verified_user.auth_user_id}, Org Name: {emp.organization.verified_user.full_name}")
