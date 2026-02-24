import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider
from provider_dynamic_fields.models import ProviderFacility

def check_raj_facilities():
    try:
        provider = ServiceProvider.objects.get(verified_user__email='raj@gmail.com')
        print(f"--- Checking Facilities for {provider.verified_user.email} ---")
        facs = ProviderFacility.objects.filter(provider=provider.verified_user)
        for f in facs:
            print(f"ID: {f.id}, Name: {f.name}, Category: {f.category.name if f.category else 'N/A'}, Image: {f.image}")
    except ServiceProvider.DoesNotExist:
        print("Raj provider not found")

if __name__ == "__main__":
    check_raj_facilities()
