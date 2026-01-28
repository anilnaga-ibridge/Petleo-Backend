
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService

# 1. Rename the CORRECT Veterinary Template (ID 2dff...)
# Use filter to be safe, though get() is fine if ID is unique
vet_svc = ProviderTemplateService.objects.filter(super_admin_service_id="2dff446f-c95f-4310-ba4d-05e3395dd7eb").first()
if vet_svc:
    print(f"Found Target Vet Template: {vet_svc.name} (ID: {vet_svc.super_admin_service_id})")
    vet_svc.name = "VETERINARY_CORE"
    vet_svc.save()
    print("✅ Renamed to 'VETERINARY_CORE'")
else:
    print("❌ Target Vet Template (2dff...) not found.")

# 2. Fix 'Trainning' Typo
train_svc = ProviderTemplateService.objects.filter(name__iexact="Trainning").first()
if train_svc:
    print(f"Found Typo Template: {train_svc.name} (ID: {train_svc.super_admin_service_id})")
    train_svc.name = "TRAINING" # Fix typo
    train_svc.save()
    print("✅ Renamed to 'TRAINING'")
else:
    print("ℹ️ 'Trainning' template not found (maybe already fixed).")
