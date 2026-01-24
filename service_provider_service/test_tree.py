print("Script started")
import os
import django
import sys

print("Setting DJANGO_SETTINGS_MODULE")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
print("Calling django.setup()")
django.setup()
print("django.setup() complete")

from service_provider.models import OrganizationEmployee, VerifiedUser
from service_provider.views import get_my_permissions
from rest_framework.test import APIRequestFactory
import json

print("Import complete")
factory = APIRequestFactory()
# ... rest of script ...
