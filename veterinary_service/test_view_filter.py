import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken

from django.contrib.auth import get_user_model
from veterinary.views import StaffAssignmentViewSet
from veterinary.models import Clinic

User = get_user_model()
org_uuid = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"

# 1. Create/Get the shadow user
user, created = User.objects.get_or_create(username=org_uuid)
user.role = 'ORGANIZATION' # CRITICAL FIX FOR TEST
print(f"User: username={user.username}, id={user.id}")

# 2. Simulate a request with a token
factory = APIRequestFactory()
request = factory.get('/api/veterinary/assignments/')

# Manually attach user and auth like DRF does
request.user = user
# Create a dummy token object that has a .get method
class DummyToken:
    def __init__(self, data):
        self.data = data
    def get(self, key, default=None):
        return self.data.get(key, default)

request.auth = DummyToken({'user_id': org_uuid})

view = StaffAssignmentViewSet()
view.request = request
view.format_kwarg = None

qs = view.get_queryset()
print(f"Queryset count with auth.get('user_id'): {qs.count()}")

# 3. Simulate request WITHOUT auth.get (the potential failure case)
request.auth = None
qs_fail = view.get_queryset()
print(f"Queryset count without auth (falls back to user.id): {qs_fail.count()}")
