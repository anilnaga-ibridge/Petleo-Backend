import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, Clinic, VeterinaryStaff

print("All Assignments in DB:")
for a in StaffClinicAssignment.objects.all():
    print(f"ID={a.id} StaffAuthID={a.staff.auth_user_id} ClinicOrgID={a.clinic.organization_id}")

