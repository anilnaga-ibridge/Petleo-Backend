import os
import django
import sys

# Set up Django environment
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderFacility, ProviderPricing, ProviderTemplateFacility, ProviderTemplatePricing

def repair():
    print("--- Repairing Boarding Prices ---")
    
    targets = [
        {"name": "Day Care", "sa_id": "8473ebe3-ad1d-4b9b-b8a9-76c9615682a5", "price": 899.00},
        {"name": "Night Stay", "sa_id": "2d385a36-7e42-4069-90f4-c824b384e2e5", "price": 599.00},
    ]
    
    for t in targets:
        # Update Template Facility
        tf = ProviderTemplateFacility.objects.filter(super_admin_facility_id=t["sa_id"]).first()
        if tf:
            tf.base_price = t["price"]
            tf.save()
            print(f"Updated Template Facility '{t['name']}' to {t['price']}")
            
            # Update/Create Template Pricing
            tp = ProviderTemplatePricing.objects.filter(facility=tf).first()
            if tp:
                tp.price = t["price"]
                tp.save()
                print(f"Updated existing Template Pricing for '{t['name']}' to {t['price']}")
            else:
                tp = ProviderTemplatePricing.objects.create(
                    facility=tf,
                    super_admin_pricing_id=f"REPAIR_AUTO_{t['sa_id']}",
                    service=tf.category.service,
                    category=tf.category,
                    price=t["price"],
                    billing_unit="PER_SESSION",
                    duration_minutes=60,
                    service_duration_type="MINUTES",
                    pricing_model="PER_UNIT"
                )
                print(f"Created new Template Pricing for '{t['name']}' to {t['price']}")

    # 2. Update Actual Records
    for t in targets:
        # Update Real Facility
        facs = ProviderFacility.objects.filter(name=t["name"])
        for f in facs:
            f.price = t["price"]
            f.base_price = t["price"]
            f.save()
            print(f"Updated Real Facility '{t['name']}' (ID: {f.id}) to {t['price']}")
            
            # Update Real Pricing Rules
            prices = ProviderPricing.objects.filter(facility=f)
            for p in prices:
                p.price = t["price"]
                p.save()
                print(f"Updated Real Pricing rule for '{t['name']}' (ID: {p.id}) to {t['price']}")

    print("--- Repair Completed ---")

if __name__ == "__main__":
    repair()
