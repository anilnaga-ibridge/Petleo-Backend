import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility,
    ProviderCapabilityAccess
)

print("--- ProviderTemplateService ---")
services = ProviderTemplateService.objects.all()
print(f"Count: {services.count()}")
for s in services:
    print(f"ID: {s.super_admin_service_id}, Name: {s.name}, Display: {s.display_name}")

print("\n--- VerifiedUser Permissions ---")
target_id = "7470623a-ee4b-4922-99f5-3ce2f17171d7"
users = VerifiedUser.objects.filter(auth_user_id=target_id)
for u in users:
    print(f"User: {u.email} (ID: {u.auth_user_id}) ({u.role})")
    caps = ProviderCapabilityAccess.objects.filter(user=u)
    print(f"  Capabilities (Table): {caps.count()} items")
    
    # Group by service
    service_ids = caps.values_list('service_id', flat=True).distinct()
    print(f"  Distinct Services: {len(service_ids)}")
    for sid in service_ids:
        try:
            svc = ProviderTemplateService.objects.get(super_admin_service_id=sid)
            print(f"    - {svc.display_name} ({sid})")
        except ProviderTemplateService.DoesNotExist:
            print(f"    - UNKNOWN SERVICE ({sid})")
