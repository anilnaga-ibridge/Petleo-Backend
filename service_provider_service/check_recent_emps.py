import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee

emps = OrganizationEmployee.objects.all().order_by('-id')[:5]
for emp in emps:
    print(f"ID: {emp.id} | Name: {emp.full_name} | Status: {emp.status} | Joined: {emp.joined_at}")
