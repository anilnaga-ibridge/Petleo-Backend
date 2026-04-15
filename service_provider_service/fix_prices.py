import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderPricing, ProviderFacility

fac = ProviderFacility.objects.filter(name="Trick Training").first()
if fac:
    pricing = ProviderPricing.objects.filter(facility=fac).first()
    if pricing:
        pricing.price = 2999.00
        pricing.save()
        print(f"Updated {fac.name} to 2999.00")

fac2 = ProviderFacility.objects.filter(name="Guard Training").first()
if fac2:
    pricing = ProviderPricing.objects.filter(facility=fac2).first()
    if pricing:
        pricing.price = 5000.00
        pricing.save()
        print(f"Updated {fac2.name} to 5000.00")
