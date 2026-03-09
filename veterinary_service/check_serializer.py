import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory

from veterinary.models import StaffClinicAssignment
from veterinary.serializers import StaffClinicAssignmentSerializer

# Fake request object
class DummyUser:
    id = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec" # Anil Naga org
    role = "organization"
    is_authenticated = True

class DummyRequest:
    user = DummyUser()
    auth = {"user_id": "0bff4c7a-40cf-4471-aab1-9d036da2e0ec"}

assignments = StaffClinicAssignment.objects.filter(clinic__organization_id="0bff4c7a-40cf-4471-aab1-9d036da2e0ec")
serializer = StaffClinicAssignmentSerializer(assignments, many=True, context={'request': DummyRequest()})
for i, data in enumerate(serializer.data[:5]):
    print(f"Index {i}: staff_auth_id='{data.get('staff_auth_id')}', clinic='{data.get('clinic_name')}'")

