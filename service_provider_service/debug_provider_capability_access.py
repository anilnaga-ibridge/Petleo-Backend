import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess
from django.db import connection

# Find the user
user = VerifiedUser.objects.filter(email__icontains='anil').first()
if not user:
    print("Could not find user")
    exit()

print(f"User: {user.email} (Auth ID: {user.auth_user_id})")

# Get capabilities
caps = ProviderCapabilityAccess.objects.filter(user=user)
print(f"Total caps: {caps.count()}")

print("\n--- Capabilities ---")
for cap in caps:
    print(f"Service: {cap.service_id}, Cat: {cap.category_id}, Fac: {cap.facility_id}")
    print(f"  View: {cap.can_view}, Create: {cap.can_create}, Edit: {cap.can_edit}, Delete: {cap.can_delete}")

