import os
import django
import json

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_services.models import Capability

def seed_capabilities():
    print("--- Seeding Standardized Capabilities from JSON (Super Admin) ---")
    
    json_path = os.path.join(os.path.dirname(__file__), "capabilities.json")
    with open(json_path, "r") as f:
        capabilities_data = json.load(f)

    for data in capabilities_data:
        key = data["key"]
        cap, created = Capability.objects.update_or_create(
            key=key,
            defaults={
                "label": data["label"],
                "description": data["description"],
                "group": data["group"],
                "service": data.get("service", "VETERINARY")
            }
        )
        print(f"{'Created' if created else 'Updated'}: {key} -> [{cap.service}] [{cap.group}] {cap.label}")

if __name__ == "__main__":
    seed_capabilities()
