import os
import sys
import django
from django.db import transaction

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_facilities.models import Facility
from dynamic_categories.models import Category
from dynamic_pricing.models import PricingRule

@transaction.atomic
def migrate():
    print("--- Starting Facility Migration ---")
    facilities = Facility.objects.all()
    count = 0
    updated = 0
    
    for fac in facilities:
        count += 1
        print(f"Processing: {fac.name} (Service: {fac.service.display_name})")
        
        # Strategy 1: Look for PricingRule linking this Facility to a Category
        pricing = PricingRule.objects.filter(facility=fac, category__isnull=False).first()
        
        target_cat = None
        
        if pricing:
            target_cat = pricing.category
            print(f"  -> Found via Pricing: {target_cat.name}")
        else:
            # Strategy 2: Get any category for this service
            target_cat = Category.objects.filter(service=fac.service).first()
            if target_cat:
                print(f"  -> Falling back to Service Category: {target_cat.name}")
            else:
                # Strategy 3: Create 'General' category
                print(f"  -> No category found. Creating 'General'...")
                target_cat = Category.objects.create(
                    service=fac.service,
                    name="General",
                    description="Auto-generated category for migration",
                    is_active=True
                )
        
        if target_cat:
            fac.category = target_cat
            fac.save()
            updated += 1
            
    print(f"--- Migration Complete. Updated {updated}/{count} Facilities. ---")

if __name__ == "__main__":
    migrate()
