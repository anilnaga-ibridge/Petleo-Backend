import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderDocument

data = {}
for doc in ProviderDocument.objects.all():
    data[str(doc.id)] = str(doc.definition_id) if doc.definition_id else None

with open("docs_backfill.json", "w") as f:
    json.dump(data, f, indent=4)

print(f"Exported {len(data)} document mappings to docs_backfill.json")
