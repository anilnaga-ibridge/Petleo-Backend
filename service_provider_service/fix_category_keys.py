import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory

def fix_category_keys():
    print("🚀 Standardizing Category Keys (Veterinary Service)...")
    
    # Explicit Mapping for Veterinary Modules
    # These must match the keys in role_templates.py and frontend navigation
    MAPPING = {
        "VISITS": "VETERINARY_VISITS",
        "PATIENTS": "VETERINARY_PATIENTS",
        "VETERINARY_ASSISTANT": "VETERINARY_VITALS",
        "DOCTOR_STATION": "VETERINARY_DOCTOR",
        "PHARMACY": "VETERINARY_PHARMACY",
        "PHARMACY_STORE": "VETERINARY_PHARMACY_STORE",
        "LABS": "VETERINARY_LABS",
        "SCHEDULE": "VETERINARY_SCHEDULE",
        "ONLINE_CONSULT": "VETERINARY_ONLINE_CONSULT",
        "OFFLINE_VISITS": "VETERINARY_OFFLINE_VISIT", # Note: singular in role template
        "MEDICINE_REMINDERS": "VETERINARY_MEDICINE_REMINDERS",
        "CLINIC_SETTINGS": "VETERINARY_ADMIN_SETTINGS",
        "METADATA_MANAGEMENT": "VETERINARY_METADATA",
    }
    
    updated_count = 0
    for short_key, long_key in MAPPING.items():
        # Update by partial match or exact match to be safe
        cats = ProviderTemplateCategory.objects.filter(category_key=short_key)
        for cat in cats:
            print(f"   🔄 Updating: {cat.name} | {cat.category_key} -> {long_key}")
            cat.category_key = long_key
            cat.save()
            updated_count += 1
            
    print(f"\n✅ Standardized {updated_count} veterinary category keys.")

if __name__ == "__main__":
    fix_category_keys()
