import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider
from provider_dynamic_fields.models import ProviderCapabilityAccess

def check_caps():
    provider = ServiceProvider.objects.first()
    user = provider.verified_user
    print(f"--- Checking Caps for {user.email} ---")
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    services = set()
    for c in caps:
        services.add(c.service_id)
        print(f"Service: {c.service_id}, Category: {c.category_id}, Facility: {c.facility_id}")
    
    print(f"Unique Services: {services}")
    if '8da6c82b-2136-4a14-9670-2973682107a6' in [str(s) for s in services]:
        print("Grooming Service is in Caps!")
    else:
        print("Grooming Service is NOT in Caps!")

if __name__ == "__main__":
    check_caps()
