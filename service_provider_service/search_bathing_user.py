import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderCategory, ProviderFacility

def search_bathing_with_user():
    print("--- Searching for Bathing with User ---")
    cats = ProviderCategory.objects.filter(name__icontains='Bathing')
    for c in cats:
        print(f"Category: {c.name}, User: {c.provider.email if c.provider else 'N/A'}")
        facs = ProviderFacility.objects.filter(category=c)
        for f in facs:
            print(f"  Facility: {f.name}, Provider: {f.provider.email if f.provider else 'N/A'}, Image: {f.image}")

if __name__ == "__main__":
    search_bathing_with_user()
