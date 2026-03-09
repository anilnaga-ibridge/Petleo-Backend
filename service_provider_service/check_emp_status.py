import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee

print("Checking statuses of employees:")
for emp in OrganizationEmployee.objects.all():
    print(f"{emp.full_name} ({emp.email}): status={emp.status}")
