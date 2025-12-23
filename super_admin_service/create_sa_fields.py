import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_fields.models import ProviderFieldDefinition

def create_fields():
    targets = ["individual", "organization"]
    
    fields = [
        {"name": "email", "label": "Email", "type": "text", "required": True},
        {"name": "organization", "label": "Organization", "type": "text", "required": False},
        {"name": "phone_number", "label": "Phone Number", "type": "text", "required": True},
        {"name": "address", "label": "Address", "type": "text", "required": True},
        {"name": "state", "label": "State", "type": "text", "required": True},
        {"name": "zip_code", "label": "Zip Code", "type": "text", "required": True},
        {"name": "country", "label": "Country", "type": "dropdown", "options": ["USA", "Canada", "UK", "India", "Australia"], "required": True},
        {"name": "language", "label": "Language", "type": "dropdown", "options": ["English", "Spanish", "French", "German", "Hindi"], "required": True},
        {"name": "timezone", "label": "Timezone", "type": "dropdown", "options": ["(GMT-11:00) International Date Line West", "(GMT-11:00) Midway Island", "(GMT-10:00) Hawaii"], "required": True},
        {"name": "currency", "label": "Currency", "type": "dropdown", "options": ["USD", "EUR", "GBP", "INR", "AUD"], "required": True},
    ]

    for target in targets:
        print(f"Creating fields for {target}...")
        for f in fields:
            # Skip organization field for individual if desired, but frontend has it.
            # Skip phone_number/address if they already exist (we'll update_or_create)
            
            obj, created = ProviderFieldDefinition.objects.update_or_create(
                target=target,
                name=f["name"],
                defaults={
                    "label": f["label"],
                    "field_type": f["type"],
                    "is_required": f["required"],
                    "options": f.get("options", []),
                    "order": 0
                }
            )
            print(f"  {'Created' if created else 'Updated'} {f['name']}")

    # Fix typo 'addres' -> delete it
    ProviderFieldDefinition.objects.filter(name="addres").delete()
    print("Deleted typo 'addres'")

if __name__ == "__main__":
    create_fields()
