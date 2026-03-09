import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import StaffClinicAssignment, Clinic, VeterinaryStaff
from veterinary.serializers import StaffClinicAssignmentSerializer

# Fake request object
class DummyUser:
    id = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec" # Anil Naga org
    role = "organization"
    is_authenticated = True

class DummyRequest:
    user = DummyUser()
    auth = {"user_id": "0bff4c7a-40cf-4471-aab1-9d036da2e0ec"}

# Find a clinic
clinic = Clinic.objects.filter(organization_id="0bff4c7a-40cf-4471-aab1-9d036da2e0ec").first()
if not clinic:
    print("No clinic found for org")
    exit(1)

# Payload like frontend
payload = {
    "clinic": str(clinic.id),
    "role": "Receptionist",
    "staff_auth_id": "fake-rahul-id-1234", # Simulate Rahul
    "permissions": ["VETERINARY_CORE"],
    "specialization": "",
    "consultation_fee": 0
}

serializer = StaffClinicAssignmentSerializer(data=payload, context={'request': DummyRequest()})
if serializer.is_valid():
    print("Serializer is valid. Data:", serializer.validated_data)
    assignment = serializer.save()
    print("Saved Assignment:", assignment)
    print("Staff Auth ID created:", assignment.staff.auth_user_id)
else:
    print("Serializer errors:", serializer.errors)
