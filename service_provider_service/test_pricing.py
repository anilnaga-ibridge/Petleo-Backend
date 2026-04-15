import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderFacility, ProviderPricing

prices = ProviderPricing.objects.all().order_by('-created_at')[:10]
for p in prices:
    print(f"Pricing ID: {p.id}")
    print(f"Facility Name: {p.facility.name if p.facility else 'No Facility'}")
    print(f"Price: {p.price}")
    print(f"Model: {p.pricing_model}")
    print("-" * 20)

