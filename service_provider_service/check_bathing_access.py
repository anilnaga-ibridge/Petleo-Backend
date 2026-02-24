import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderCapabilityAccess

def check_bathing_access():
    print("--- Checking Access for Bathing ---")
    # Bathing category ID was b270b320-9102-41ec-b34f-9318925b5b24
    caps = ProviderCapabilityAccess.objects.filter(category_id='7dcf3326-2750-40db-b07a-3e0167e3f226')
    for c in caps:
        print(f"User: {c.user.email}, Service: {c.service_id}, Category: {c.category_id}, View: {c.can_view}")

if __name__ == "__main__":
    check_bathing_access()
