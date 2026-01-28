
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory

print("Searching for VETERINARY_CORE Template:")
svcs = ProviderTemplateService.objects.filter(name="VETERINARY_CORE")
if not svcs.exists():
    print("  Not found. Searching for 'VETERINARY'...")
    svcs = ProviderTemplateService.objects.filter(name="VETERINARY")

for s in svcs:
    print(f"Service: {s.name} (SA ID: {s.super_admin_service_id})")
    cats = ProviderTemplateCategory.objects.filter(service=s)
    for c in cats:
        print(f"  - Category: {c.name} (SA ID: {c.super_admin_category_id}, Cap: {c.linked_capability})")
