import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import StaffClinicAssignment, VeterinaryStaff, Clinic

print("-" * 50)
print("STAFF ASSIGNMENTS DEBUG")
print("-" * 50)

assignments = StaffClinicAssignment.objects.all()

for count, assign in enumerate(assignments, 1):
    print(f"[{count}] Staff: {assign.staff.auth_user_id} | Clinic: {assign.clinic.name}")
    print(f"    Role: {assign.role}")
    print(f"    Permissions Count: {len(assign.permissions)}")
    print(f"    Permissions: {assign.permissions}")
    print("-" * 20)

if not assignments:
    print("No assignments found.")
