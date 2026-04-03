import os
import django

# No sys.path hack needed if we run with python -m or correctly set PYTHONPATH
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_core.settings')
django.setup()

from dynamic_categories.models import Category

def backfill_category_keys():
    print("Starting Category Key Backfill (Super Admin)...")
    categories = Category.objects.filter(category_key__isnull=True) | Category.objects.filter(category_key='')
    
    count = 0
    for cat in categories:
        # Convert name to uppercase snake case
        # "Basic Boarding" -> "BOARDING_BASIC" is better than "BASIC_BOARDING" 
        # but let's stick to a simple mapping for now as it's safe.
        name = cat.name.strip().upper()
        
        # Simple reordering for known patterns
        if "BOARDING" in name and "BASIC" in name:
            key = "BOARDING_BASIC"
        elif "BOARDING" in name and "DELUXE" in name:
            key = "BOARDING_DELUXE"
        elif "BOARDING" in name and "LUXURY" in name:
            key = "BOARDING_LUXURY"
        else:
            key = name.replace(' ', '_').replace('-', '_')
            
        print(f"Assigning: '{cat.name}' -> '{key}'")
        cat.category_key = key
        cat.save()
        count += 1
    
    print(f"Completed! Updated {count} categories.")

if __name__ == "__main__":
    backfill_category_keys()
