import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, Clinic

assignment_id = "d68d2a41-acbc-40aa-b611-fec3bf6e8f8b"
try:
    a = StaffClinicAssignment.objects.get(id=assignment_id)
    print(f"Assignment found: {a.id}")
    print(f"Clinic: {a.clinic.name}")
    print(f"Clinic Org ID: {a.clinic.organization_id}")
    print(f"Staff Auth ID: {a.staff.auth_user_id}")
except StaffClinicAssignment.DoesNotExist:
    print(f"Assignment {assignment_id} not found")

print("\n--- All Assignments ---")
for a in StaffClinicAssignment.objects.all():
    print(f"{a.id} | Clinic: {a.clinic.name} | ClinicOrg: {a.clinic.organization_id} | StaffAuth: {a.staff.auth_user_id}")
