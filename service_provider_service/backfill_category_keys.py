import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider.settings')
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory

def backfill_category_keys():
    print("Starting Category Key Backfill (Provider Service)...")
    categories = ProviderTemplateCategory.objects.filter(category_key__isnull=True) | ProviderTemplateCategory.objects.filter(category_key='')
    
    count = 0
    for cat in categories:
        # Convert name to BOARDING_BASIC style
        key = cat.name.strip().upper().replace(' ', '_').replace('-', '_')
        
        # Simple suffix-based reordering for consistency (optional, but nice)
        # "BOARDING BASIC" -> BOARDING_BASIC
        # If it already looks like "BASIC_BOARDING", that's fine too.
        
        cat.category_key = key
        cat.save()
        print(f"Updated: '{cat.name}' -> '{cat.category_key}'")
        count += 1
    
    print(f"Completed! Updated {count} categories.")

if __name__ == "__main__":
    backfill_category_keys()
