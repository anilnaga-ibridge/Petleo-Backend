
import os
import django
import sys
import json

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess

user = VerifiedUser.objects.filter(auth_user_id="076875b0-ca6b-4d96-a5a5-36f29e8cd976").first()
if user:
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    print(f"User: {user.full_name}")
    print(f"Total Raw Capabilities: {caps.count()}")
    for c in caps:
        print(f"Cap: S={c.service_id} C={c.category_id} F={c.facility_id}")
        print(f"     View={c.can_view}")
else:
    print("User not found")
