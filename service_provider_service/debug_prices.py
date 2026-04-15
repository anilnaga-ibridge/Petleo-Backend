import os
import django
import sys

# Set up Django environment
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderFacility, ProviderPricing, ProviderTemplateFacility

print("=== ProviderTemplateFacility ===")
for tf in ProviderTemplateFacility.objects.all():
    print(f"ID: {tf.id}, Name: {tf.name}, BasePrice: {tf.base_price}")

print("\n=== ProviderFacility ===")
for f in ProviderFacility.objects.all():
    print(f"ID: {f.id}, Name: {f.name}, Price: {f.price}, BasePrice: {f.base_price}")

print("\n=== ProviderPricing ===")
for p in ProviderPricing.objects.all():
    print(f"ID: {p.id}, Facility: {p.facility.name if p.facility else 'None'}, Price: {p.price}, Description: {p.description}")
