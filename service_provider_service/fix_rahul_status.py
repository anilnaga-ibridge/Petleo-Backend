import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser

# Find Rahul (can be full_name or email containing rahul or role doctor)
employees = OrganizationEmployee.objects.filter(full_name__icontains="rahul", role__icontains="doctor", status="PENDING")
if not employees.exists():
    employees = OrganizationEmployee.objects.filter(full_name__icontains="rahul", status="PENDING")

count = 0
for emp in employees:
    emp.status = "ACTIVE"
    if not emp.joined_at:
        emp.joined_at = timezone.now()
    emp.save()
    count += 1
    print(f"Fixed employee {emp.full_name} ({emp.email}), set to ACTIVE with joined_at={emp.joined_at}")

if count == 0:
    print("No pending employees named Rahul found.")
