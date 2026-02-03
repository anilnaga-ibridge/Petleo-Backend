
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplatePricing, ProviderTemplateFacility

def verify_prices():
    print("--- Verifying Prices for User ---")
    
    # We'll just look at all prices for the specific service/category we know about
    # Service: Hair Cutting / Bathing
    
    all_prices = ProviderTemplatePricing.objects.all()
    print(f"Total Prices in DB: {all_prices.count()}")
    
    for p in all_prices:
        print(f"Price ID: {p.id}")
        print(f"  Super Admin ID: {p.super_admin_pricing_id}")
        print(f"  Price: {p.price}")
        print(f"  Facility: {p.facility.name if p.facility else 'None'}")
        print(f"  Category: {p.category.name if p.category else 'None'}")
        print("-" * 20)

if __name__ == "__main__":
    verify_prices()
