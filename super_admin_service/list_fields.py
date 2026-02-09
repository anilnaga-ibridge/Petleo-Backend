import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_fields.models import ProviderFieldDefinition

fields = ProviderFieldDefinition.objects.all().order_by('target', 'order')
print(f"{'Target':<15} | {'Name':<20} | {'Label':<20} | {'Required':<10}")
print("-" * 75)
for f in fields:
    print(f"{f.target:<15} | {f.name:<20} | {f.label:<20} | {str(f.is_required):<10}")
