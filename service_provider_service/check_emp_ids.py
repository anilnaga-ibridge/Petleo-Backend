import os
import django

# Set up Django for service_provider_service
# We need to find the settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from org_employees.models import OrganizationEmployee

print("--- Employees in service_provider_service ---")
for emp in OrganizationEmployee.objects.all():
    print(f"Name: {emp.full_name}, AuthID: {emp.auth_user_id}, OrgID: {emp.organization_id}")
