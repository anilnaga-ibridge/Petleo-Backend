import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser
from service_provider.serializers import OrganizationEmployeeSerializer

# Fake request object
class DummyUser:
    auth_user_id = "0bff4c7a-40cf-4471-aab1-9d036da2e0ec" # Anil Naga org
    role = "organization"
    is_authenticated = True

class DummyRequest:
    user = DummyUser()
    auth = {"user_id": "0bff4c7a-40cf-4471-aab1-9d036da2e0ec"}

employees = OrganizationEmployee.objects.filter(organization__verified_user__auth_user_id="0bff4c7a-40cf-4471-aab1-9d036da2e0ec")
serializer = OrganizationEmployeeSerializer(employees, many=True, context={'request': DummyRequest()})
for i, data in enumerate(serializer.data[:5]):
    print(f"Index {i}: auth_user_id='{data.get('auth_user_id')}', full_name='{data.get('full_name')}'")
