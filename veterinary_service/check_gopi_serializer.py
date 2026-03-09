import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory

from veterinary.models import StaffClinicAssignment, Clinic
from veterinary.serializers import StaffClinicAssignmentSerializer

# Fake request object for Gopi
class DummyUser:
    id = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed" # Gopi org
    role = "organization"
    is_authenticated = True

class DummyRequest:
    user = DummyUser()
    auth = {"user_id": "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"}

assignments = StaffClinicAssignment.objects.filter(clinic__organization_id="87b9cb5d-ee9e-4e20-bf22-646b30b793ed")
serializer = StaffClinicAssignmentSerializer(assignments, many=True, context={'request': DummyRequest()})
print("Assignments for Gopi:")
for a in serializer.data:
    if "5c3b54b9" in a.get("staff_auth_id", ""):
        print(a)
