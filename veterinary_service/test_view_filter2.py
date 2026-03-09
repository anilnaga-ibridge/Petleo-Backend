import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()
from rest_framework.test import APIRequestFactory
from veterinary.views import StaffAssignmentViewSet
from veterinary.models import VeterinaryStaff, Clinic, StaffClinicAssignment
from django.contrib.auth import get_user_model
User = get_user_model()
# Ensure a user exists with username as UUID
test_uuid = '87b9cb5d-ee9e-4e20-bf22-646b30b793ed'
user, _ = User.objects.get_or_create(username=test_uuid)
user.role = 'ORGANIZATION'
# Create a clinic belonging to this organization
clinic, _ = Clinic.objects.get_or_create(name='Test Clinic', organization_id=test_uuid)
# Create a staff and assignment
staff, _ = VeterinaryStaff.objects.get_or_create(auth_user_id='5c3b54b9-aa99-441d-8598-df3aea0b59fd')
assignment, _ = StaffClinicAssignment.objects.update_or_create(
    staff=staff, clinic=clinic, defaults={'role':'Veterinary Doctor', 'permissions':['VETERINARY_CORE']})
# Mock request
factory = APIRequestFactory()
request = factory.get('/api/veterinary/assignments/')
request.query_params = {}
request.user = user
request.auth = {'user_id': test_uuid}
view = StaffAssignmentViewSet()
view.request = request
qs = view.get_queryset()
print('Queryset count:', qs.count())
for a in qs:
    print('Assignment:', a.id, a.staff.auth_user_id, a.clinic.name)
