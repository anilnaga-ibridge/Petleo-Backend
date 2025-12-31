
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import LocalFieldDefinition, LocalDocumentDefinition

def check_definitions():
    print("Checking LocalFieldDefinition...")
    fields = LocalFieldDefinition.objects.all()
    print(f"Total Fields: {fields.count()}")
    for f in fields:
        print(f"- {f.target}: {f.label} ({f.field_type})")

    print("\nChecking LocalDocumentDefinition...")
    docs = LocalDocumentDefinition.objects.all()
    print(f"Total Docs: {docs.count()}")
    for d in docs:
        print(f"- {d.target}: {d.label}")

if __name__ == "__main__":
    check_definitions()
