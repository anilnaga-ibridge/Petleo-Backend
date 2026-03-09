import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, Clinic, VeterinaryStaff

assignments = StaffClinicAssignment.objects.filter(staff__auth_user_id__isnull=False)
print("Total Assignments:", assignments.count())

print("\n--- Listing VeterinaryStaff matching rahul ---")
users = VeterinaryStaff.objects.all()
for u in users:
    if "rahul" in (u.auth_user_id or "").lower():
        print(f"Found VeterinaryStaff: {u.auth_user_id}")
        # Get their assignments
        user_assignments = StaffClinicAssignment.objects.filter(staff=u)
        for a in user_assignments:
            print(f"  -> Assigned to Clinic: {a.clinic.name} ({a.clinic.organization_id}) Role: {a.role}")

print("\nDone")
