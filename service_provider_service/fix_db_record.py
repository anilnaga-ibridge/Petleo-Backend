import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee

# Get the most recent Praveen and set to PENDING
emp = OrganizationEmployee.objects.filter(email='praveen@gmail.com').order_by('-id').first()
if emp:
    print(f"Updating employee {emp.full_name} ({emp.email}) from {emp.status} to PENDING")
    emp.status = 'PENDING'
    emp.joined_at = None
    emp.save()
    print("Done!")
