import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, Clinic, VeterinaryStaff

assignments = StaffClinicAssignment.objects.all().order_by('-created_at')[:5]

print("Last 5 assignments:")
for a in assignments:
    print(f"ID: {a.id}, Staff Auth: {a.staff.auth_user_id} - Clinic: {a.clinic.name}")

