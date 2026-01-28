
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService

print("Listing ALL Service Templates:")
for s in ProviderTemplateService.objects.all():
    print(f"Name: '{s.name}' | Display: '{s.display_name}' | ID: {s.super_admin_service_id}")
