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

doctor_permissions = [
    'VETERINARY_CORE',
    'VISITS',
    'VETERINARY_ASSISTANT',
    'DOCTOR_STATION',
    'VETERINARY_PRESCRIPTIONS',
    'LABS',
    'SCHEDULE',
    'ONLINE_CONSULT',
    'OFFLINE_VISITS'
]

for a in assignments:
    print(f"  Clinic: {a.clinic_id} | Role: {a.role}")
    print(f"  Old Perms: {a.permissions}")
    a.permissions = doctor_permissions
    a.role = 'Doctor'
    a.save()
    print(f"  New Perms: {a.permissions}")

# Also update the base staff record just in case
staff.permissions = doctor_permissions
staff.role = 'Doctor'
staff.save()
print("\n✅ Successfully updated permissions for Jhony in Veterinary Service")
