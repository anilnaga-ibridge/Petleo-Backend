
import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import FormDefinition, Clinic, VeterinaryStaff, StaffClinicAssignment, Pet, PetOwner
from django.contrib.auth import get_user_model
User = get_user_model()

print("=== DIAGNOSTIC REPORT ===")

print("\n--- Form Definitions ---")
forms = FormDefinition.objects.all()
if not forms.exists():
    print("No FormDefinitions found.")
else:
    for f in forms:
        print(f"Code: {f.code}, Name: {f.name}, Clinic: {f.clinic_id}")

print("\n--- Clinics ---")
for c in Clinic.objects.all():
    print(f"ID: {c.id}, Name: {c.name}, OrgID: {c.organization_id}")

print("\n--- Staff ---")
staff_list = VeterinaryStaff.objects.all()
if not staff_list.exists():
    print("No VeterinaryStaff found.")
else:
    for s in staff_list:
        print(f"Staff: {getattr(s, 'full_name', 'N/A')}, AuthID: {s.auth_user_id}, Role: {s.role}")

print("\n--- Staff Assignments ---")
assignments = StaffClinicAssignment.objects.all()
if not assignments.exists():
    print("No StaffClinicAssignments found.")
else:
    for a in assignments:
        print(f"Staff AuthID: {a.staff.auth_user_id}, Clinic: {a.clinic.name}, Role: {a.role}, Active: {a.is_active}")

print("\n--- Users (Auth DB) ---")
for u in User.objects.all():
    print(f"Username (UUID): {u.username}, last_login: {u.last_login}")

print("\n--- Pet Owners ---")
for po in PetOwner.objects.all()[:10]:
    print(f"Owner: {po.name}, Clinic: {po.clinic_id}, AuthID: {po.auth_user_id}")

print("\n=== END REPORT ===")
