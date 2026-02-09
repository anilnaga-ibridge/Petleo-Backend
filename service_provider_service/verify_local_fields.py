import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import LocalFieldDefinition, LocalDocumentDefinition

def check_fields():
    print("🔍 Checking Local Field Definitions in Service Provider Service...")
    
    targets = ["individual", "organization", "employee"]
    
    for target in targets:
        fields = LocalFieldDefinition.objects.filter(target=target).order_by('order')
        print(f"\n📂 Target: {target.upper()}")
        if not fields.exists():
            print("   ❌ No fields found!")
        else:
            for f in fields:
                print(f"   - {f.label} ({f.name}) [Type: {f.field_type}, Required: {f.is_required}]")

    print("\n🔍 Checking Local Document Definitions...")
    for target in targets:
        docs = LocalDocumentDefinition.objects.filter(target=target).order_by('order')
        print(f"\n📂 Target: {target.upper()}")
        if not docs.exists():
            print("   ❌ No documents found!")
        else:
            for d in docs:
                print(f"   - {d.label} ({d.key}) [Required: {d.is_required}]")

if __name__ == "__main__":
    check_fields()
