
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService

print("Searching for services with 'Training' in name or display_name:")
svcs = ProviderTemplateService.objects.filter(display_name__icontains="Training")
for s in svcs:
    print(f"Service: {s.name} (Display: {s.display_name}) SA_ID: {s.super_admin_service_id}")

svcs_typo = ProviderTemplateService.objects.filter(name__icontains="Trainning")
for s in svcs_typo:
    print(f"Service (Typo): {s.name} (Display: {s.display_name}) SA_ID: {s.super_admin_service_id}")
