import os
import django
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplatePricing

def verify_pricing():
    print("Checking ProviderTemplatePricing...")
    count = ProviderTemplatePricing.objects.count()
    print(f"Total Pricing Records: {count}")
    
    for p in ProviderTemplatePricing.objects.all():
        print(f" - {p.service.display_name}: {p.price} ({p.duration})")

if __name__ == "__main__":
    # Wait a bit for Kafka to process
    time.sleep(2)
    verify_pricing()
