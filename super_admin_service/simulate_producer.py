
import os
import sys
import django
import json
import uuid

# Setup Django for Super Admin Service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility
from dynamic_pricing.models import PricingRule

def simulate_payload():
    print("--- Simulating Producer Payload ---")
    
    # 1. Create Mock Data
    srv = Service.objects.first()
    if not srv:
        print("No Service found. Cannot simulate.")
        return

    cat = Category.objects.filter(service=srv).first()
    if not cat:
        # Create dummy
        cat = Category.objects.create(service=srv, name="Simulated Category", is_active=True)
        print("Created Dummy Category")

    fac = Facility.objects.filter(category=cat).first()
    if not fac:
        fac = Facility.objects.create(category=cat, name="Simulated Facility", is_active=True)
        print("Created Dummy Facility")

    # Create Pricing (Strict Hierarchy)
    price_strict, _ = PricingRule.objects.get_or_create(
        service=srv,
        category=cat,
        facility=fac,
        defaults={"base_price": 500.00, "is_active": True}
    )
    
    # Create Pricing (Category Level)
    price_cat, _ = PricingRule.objects.get_or_create(
        service=srv,
        category=cat,
        facility=None,
        defaults={"base_price": 300.00, "is_active": True}
    )

    print(f"Service: {srv.id}")
    print(f"Category: {cat.id}")
    print(f"Facility: {fac.id}")
    print(f"Price (Strict): {price_strict.id} (Fac: {price_strict.facility.id})")
    print(f"Price (Cat): {price_cat.id} (Fac: {price_cat.facility})")

    # 2. Run Producer Logic (Copied from purchase_publish_wrapper.py)
    templates = {
        "services": [], "categories": [], "facilities": [], "pricing": []
    }
    seen_services = {srv.id}
    seen_categories = set()
    seen_facilities = set()
    
    # Services
    templates["services"].append({"id": str(srv.id), "name": srv.name})
    
    # Categories
    categories_qs = Category.objects.filter(service__id__in=seen_services)
    for c in categories_qs:
        templates["categories"].append({"id": str(c.id), "service_id": str(c.service.id), "name": c.name})
        seen_categories.add(c.id)
        
        # Facilities
        cat_facilities = c.facilities.filter(is_active=True)
        for f in cat_facilities:
            templates["facilities"].append({"id": str(f.id), "category_id": str(c.id), "name": f.name})
            seen_facilities.add(f.id)
            print(f"Added Facility: {f.id}")

    # Pricing
    pricing_qs = PricingRule.objects.filter(service__id__in=seen_services, is_active=True)
    for price in pricing_qs:
        p_cat_id = str(price.category.id) if price.category else None
        p_fac_id = str(price.facility.id) if price.facility else None
        
        if p_fac_id and not p_cat_id and price.facility.category:
             p_cat_id = str(price.facility.category.id)

        include_price = False
        
        if not p_cat_id and not p_fac_id:
             include_price = True
        elif p_cat_id and not p_fac_id:
             if price.category.id in seen_categories:
                 include_price = True
        elif p_fac_id:
             if price.facility.id in seen_facilities:
                 include_price = True
                 
        if include_price:
            templates["pricing"].append({
                "id": str(price.id),
                "facility_id": p_fac_id,
                "price": str(price.base_price)
            })
            print(f"Added Price: {price.id} | Fac: {p_fac_id}")
        else:
            print(f"Skipped Price: {price.id} | Fac: {p_fac_id} (Reason: Fac/Cat not seen?)")

    # 3. Output
    print("\n--- Payload Result ---")
    print(json.dumps(templates, indent=2))

if __name__ == "__main__":
    simulate_payload()
