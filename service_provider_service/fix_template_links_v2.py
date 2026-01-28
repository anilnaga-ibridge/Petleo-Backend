
import os
import sys
import django
from django.conf import settings

# Setup Django if not already configured
if not settings.configured:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
    django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory

def fix_links():
    # Map Category Names to Capability Keys
    MAPPING = {
        "Vitals": "VETERINARY_VITALS",
        "Vital Signs": "VETERINARY_VITALS",
        "Visits": "VETERINARY_VISITS",
        "Appointments": "VETERINARY_VISITS",
        "Doctor": "VETERINARY_DOCTOR",
        "Consultation": "VETERINARY_DOCTOR",
        "Labs": "VETERINARY_LABS",
        "Pharmacy": "VETERINARY_PHARMACY",
        "Prescriptions": "VETERINARY_PRESCRIPTIONS",
    }
    
    print("--- Fixing Template Links ---")
    
    for name, cap_key in MAPPING.items():
        # Case insensitive search
        cats = ProviderTemplateCategory.objects.filter(name__iexact=name)
        for cat in cats:
            if cat.linked_capability != cap_key:
                print(f"Updating Category '{cat.name}' ID={cat.id}: {cat.linked_capability} -> {cap_key}")
                cat.linked_capability = cap_key
                cat.save()
            else:
                print(f"Category '{cat.name}' already linked to {cap_key}")

if __name__ == "__main__":
    fix_links()
