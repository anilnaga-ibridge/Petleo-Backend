
import os
import sys
import django
from django.db.models import Q

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory

def fix_links():
    print("🔧 Fixing ProviderTemplateCategory links...")
    
    # Heuristic Rules
    rules = [
        ("Day Care", "DAYCARE"),
        ("DayCare", "DAYCARE"),
        ("Grooming", "GROOMING"),
        ("Cutting", "GROOMING"), # e.g. Nail Cutting
        ("Bath", "GROOMING"),
        ("Training", "TRAINING"),
        ("Boarding", "BOARDING"),
        ("Reception", "VETERINARY_VISITS"), # Default fallback
    ]
    
    count = 0
    # Process only those with missing links
    cats = ProviderTemplateCategory.objects.filter(linked_capability__isnull=True)
    
    print(f"📦 Found {cats.count()} categories with missing links.")
    
    for c in cats:
        name = c.name
        fixed = False
        for keyword, key in rules:
            if keyword.lower() in name.lower():
                c.linked_capability = key
                c.save()
                print(f"   ✅ Linked '{name}' -> {key}")
                fixed = True
                count += 1
                break
        
        if not fixed:
            print(f"   ⚠️  Could not infer link for '{name}'")

    print(f"\n🎉 Fixed {count} categories.")

if __name__ == "__main__":
    fix_links()
