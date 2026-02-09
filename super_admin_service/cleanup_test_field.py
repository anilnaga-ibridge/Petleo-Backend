import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_fields.models import ProviderFieldDefinition

def cleanup():
    print("🧹 Cleaning up test fields...")
    deleted, _ = ProviderFieldDefinition.objects.filter(name__startswith="test_field_").delete()
    print(f"✅ Deleted {deleted} test fields.")

if __name__ == "__main__":
    cleanup()
