import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment

# Simulate what the new get_queryset does
# This is what request.auth.get('user_id') returns for the logged-in Gopi user
org_id = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"

qs = StaffClinicAssignment.objects.filter(clinic__organization_id=org_id)
print(f"Count for org_id={org_id}: {qs.count()}")
for a in qs:
    print(f"  - Staff: {a.staff.auth_user_id}, Clinic: {a.clinic.name}, staff_auth_id (serialized): {a.staff.auth_user_id}")
