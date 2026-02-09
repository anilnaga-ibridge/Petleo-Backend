import os
import django
import sys
import uuid
import time

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_fields.models import ProviderFieldDefinition

def create_field():
    print("🚀 Creating Test Field in Super Admin Service...")
    
    field_name = f"test_field_{int(time.time())}"
    field, created = ProviderFieldDefinition.objects.get_or_create(
        name=field_name,
        defaults={
            "target": "individual",
            "label": "Test Field Sync",
            "field_type": "text",
            "is_required": False,
            "order": 999
        }
    )
    
    if created:
        print(f"✅ Created field: {field.name} (ID: {field.id})")
        print("⏳ Waiting 5 seconds for Kafka sync...")
        time.sleep(5)
    else:
        print(f"⚠️ Field already exists: {field.name}")

if __name__ == "__main__":
    create_field()
