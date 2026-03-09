import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, Clinic, VeterinaryStaff

assignments = StaffClinicAssignment.objects.filter(staff__auth_user_id__isnull=False)
org_id = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec" 

print("Total Assignments for Anil Naga Org:")

for a in StaffClinicAssignment.objects.filter(clinic__organization_id=org_id):
    print(f"- Assignment ID: {a.id}")
    print(f"  staff__auth_user_id: {a.staff.auth_user_id if a.staff else 'NO STAFF'}")
    print(f"  clinic name: {a.clinic.name}")
    print(f"  role: {a.role}")

from veterinary.serializers import StaffClinicAssignmentSerializer

# Fake request object
class DummyUser:
    id = org_id
    role = "organization"
    is_authenticated = True

class DummyRequest:
    user = DummyUser()
    auth = {"user_id": org_id}

serializer = StaffClinicAssignmentSerializer(
    StaffClinicAssignment.objects.filter(clinic__organization_id=org_id), 
    many=True, 
    context={'request': DummyRequest()}
)

print("\n--- Serialized Data (First 3) ---")
for x in serializer.data[:3]:
    print(x)
