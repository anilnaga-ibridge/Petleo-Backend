import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService

org = VerifiedUser.objects.get(email='dhatha@gmail.com')
print(f"Org Caps via Method: {org.get_all_plan_capabilities()}")

caps = ProviderCapabilityAccess.objects.filter(user=org)
print(f"ProviderCapabilityAccess Count: {caps.count()}")

services = caps.filter(service_id__isnull=False, category_id__isnull=True, can_view=True).values_list('service_id', flat=True)
print(f"Service IDs: {list(services)}")

if services:
    service_names = ProviderTemplateService.objects.filter(super_admin_service_id__in=services).values_list('name', 'display_name')
    print(f"Service Names from Templates: {list(service_names)}")
