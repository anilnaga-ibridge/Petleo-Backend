import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment

staff = VeterinaryStaff.objects.filter(auth_user_id='938c07c7-271c-4db7-adba-da11ac5999bd').first()
if not staff:
    print('Staff not found in VeterinaryService')
    exit()

print(f"Staff: {staff.full_name} | Role: {staff.role} | Clinic: {staff.clinic_id}")
print(f"Permissions on staff record: {staff.permissions}")

assignments = StaffClinicAssignment.objects.filter(staff=staff)
print(f"\nAssignments: {assignments.count()}")
for a in assignments:
    print(f"  Clinic: {a.clinic_id} | Role: {a.role}")
    print(f"  Perms: {a.permissions}")

