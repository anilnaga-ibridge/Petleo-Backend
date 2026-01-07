
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser

print("--- OrganizationEmployee Roles ---")
employees = OrganizationEmployee.objects.all()
for emp in employees:
    print(f"Name: {emp.full_name} | Role: {emp.role} | Status: {emp.status}")

print("\n--- VerifiedUser Roles ---")
users = VerifiedUser.objects.filter(role__in=["employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "lab tech", "pharmacy", "vitalsstaff", "vitals staff"])
for user in users:
    print(f"Name: {user.full_name} | Role: {user.role} | Email: {user.email}")
