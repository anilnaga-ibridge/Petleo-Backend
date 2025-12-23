import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess

try:
    print("Fetching first VerifiedUser...")
    user = VerifiedUser.objects.first()
    if user:
        print(f"Found user: {user.email} (ID: {user.auth_user_id})")
        print("Checking capabilities...")
        caps = user.capabilities.all()
        print(f"Capabilities count: {caps.count()}")
        for cap in caps:
            print(f" - Plan: {cap.plan_id}, Service: {cap.service_id}")
    else:
        print("No VerifiedUser found.")

except Exception as e:
    import traceback
    traceback.print_exc()
