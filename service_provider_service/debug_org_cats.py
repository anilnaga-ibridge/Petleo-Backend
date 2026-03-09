import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory, ProviderTemplateService

org = VerifiedUser.objects.get(email='dhatha@gmail.com')

cat_ids = org.capabilities.filter(category_id__isnull=False).values_list('category_id', flat=True)
print(f"Cat IDs count: {cat_ids.count()}")

categories = ProviderTemplateCategory.objects.filter(super_admin_category_id__in=cat_ids)
for cat in categories:
    print(f"Cat: {cat.name} -> {cat.linked_capability}")

linked_caps = set(categories.exclude(linked_capability__isnull=True).values_list('linked_capability', flat=True))
print(f"Linked Caps: {linked_caps}")

service_ids = org.capabilities.filter(service_id__isnull=False, category_id__isnull=True, can_view=True).values_list('service_id', flat=True)
for sid in service_ids:
    svc = ProviderTemplateService.objects.filter(super_admin_service_id=sid).first()
    if svc:
        print(f"Service: {svc.name} -> {svc.display_name}")

