import os
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import Capability

import json

def seed_capabilities():
    print("--- Seeding Standardized Capabilities from JSON ---")
    
    json_path = os.path.join(os.path.dirname(__file__), "capabilities.json")
    with open(json_path, "r") as f:
        capabilities_data = json.load(f)

    for key, data in capabilities_data.items():
        cap, created = Capability.objects.update_or_create(
            key=key,
            defaults={
                "label": data["label"],
                "description": data["description"],
                "group": data["group"]
            }
        )
        print(f"{'Created' if created else 'Updated'}: {key} -> [{cap.group}] {cap.label}")

if __name__ == "__main__":
    seed_capabilities()
