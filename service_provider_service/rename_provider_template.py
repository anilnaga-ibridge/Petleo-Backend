
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService

# Find the VETERINARY template
svc = ProviderTemplateService.objects.filter(name__iexact="VETERINARY").first()

if svc:
    print(f"Found Template: {svc.name} (ID: {svc.super_admin_service_id})")
    print(f"Current Display: {svc.display_name}")
    
    # Rename to VETERINARY_CORE
    svc.name = "VETERINARY_CORE"
    svc.save()
    print("✅ Successfully renamed Template to VETERINARY_CORE")
else:
    print("Template 'VETERINARY' not found. Checking for 'VETERINARY_CORE'...")
    core = ProviderTemplateService.objects.filter(name__iexact="VETERINARY_CORE").first()
    if core:
        print(f"Template is already VETERINARY_CORE (ID: {core.super_admin_service_id})")
    else:
        print("❌ No Veterinary generic template found.")
