import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import Clinic, StaffClinicAssignment

print("--- Clinics in DB ---")
for clinic in Clinic.objects.all():
    print(f"Clinic: {clinic.name}, ID: {clinic.id}, OrgID: {clinic.organization_id}")

print("\n--- Assignments in DB ---")
for assignment in StaffClinicAssignment.objects.all():
    print(f"Assignment: Staff={assignment.staff.auth_user_id}, Clinic={assignment.clinic.name}, ClinicOrg={assignment.clinic.organization_id}")
