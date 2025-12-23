import os
import django
import requests
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import LocalFieldDefinition

SUPER_ADMIN_URL = "http://127.0.0.1:8003/api/superadmin/definitions/public/"

def sync_definitions():
    print("Fetching definitions from SuperAdmin...")
    try:
        # Fetch for individual
        resp = requests.get(f"{SUPER_ADMIN_URL}?target=individual")
        if resp.status_code != 200:
            print(f"Failed to fetch: {resp.status_code} {resp.text}")
            return

        data = resp.json()
        print(f"Found {len(data)} definitions.")

        for item in data:
            print(f"Syncing {item['name']} ({item['label']})...")
            LocalFieldDefinition.objects.update_or_create(
                id=item['id'],
                defaults={
                    "target": item['target'],
                    "name": item['name'],
                    "label": item['label'],
                    "field_type": item['field_type'],
                    "is_required": item['is_required'],
                    "options": item.get('options', []),
                    "order": item.get('order', 0),
                    "help_text": item.get('help_text', ""),
                }
            )
        print("Sync complete for Fields.")

    except Exception as e:
        print(f"Error syncing fields: {e}")

    print("Fetching DOCUMENT definitions from SuperAdmin...")
    try:
        from provider_dynamic_fields.models import LocalDocumentDefinition
        DOC_URL = "http://127.0.0.1:8003/api/superadmin/definitions/documents/public/"
        
        # Fetch for individual
        resp = requests.get(f"{DOC_URL}?target=individual")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found {len(data)} individual docs.")
            for item in data:
                LocalDocumentDefinition.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        "target": item['target'],
                        "key": item['key'],
                        "label": item['label'],
                        "is_required": item['is_required'],
                        "allow_multiple": item.get('allow_multiple', False),
                        "allowed_types": item.get('allowed_types', []),
                        "order": item.get('order', 0),
                        "help_text": item.get('help_text', ""),
                    }
                )

        # Fetch for organization
        resp = requests.get(f"{DOC_URL}?target=organization")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found {len(data)} organization docs.")
            for item in data:
                LocalDocumentDefinition.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        "target": item['target'],
                        "key": item['key'],
                        "label": item['label'],
                        "is_required": item['is_required'],
                        "allow_multiple": item.get('allow_multiple', False),
                        "allowed_types": item.get('allowed_types', []),
                        "order": item.get('order', 0),
                        "help_text": item.get('help_text', ""),
                    }
                )
        print("Sync complete for Documents.")

    except Exception as e:
        print(f"Error syncing documents: {e}")

if __name__ == "__main__":
    sync_definitions()
