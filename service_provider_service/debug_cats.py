import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory

cats = ProviderTemplateCategory.objects.filter(name__icontains='veterinary')
for cat in cats:
    print(f"Template Name: {cat.name}")

