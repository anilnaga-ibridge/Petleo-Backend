import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, AllowedService
from provider_dynamic_fields.models import ProviderTemplateService

def debug_allowed():
    print("--- Debugging Allowed Services Logic ---")
    
    user = VerifiedUser.objects.filter(email='nagaanil29@gmail.com').first()
    if not user:
        print("User not found")
        return

    print(f"User: {user.email}")
    
    # 1. Get services from Capabilities (Plan-based)
    capability_service_ids = set()
    if hasattr(user, 'capabilities'):
        capability_service_ids = set(user.capabilities.values_list('service_id', flat=True).distinct())
    print(f"Capability Service IDs: {capability_service_ids}")
    
    # 2. Get services from AllowedService (Direct assignment)
    allowed_service_ids = set(AllowedService.objects.filter(verified_user=user).values_list('service_id', flat=True))
    print(f"Allowed Service IDs: {allowed_service_ids}")
    
    # Merge all IDs
    all_service_ids = capability_service_ids.union(allowed_service_ids)
    print(f"Total Unique IDs: {len(all_service_ids)}")
    
    # Fetch details from templates
    services = ProviderTemplateService.objects.filter(super_admin_service_id__in=all_service_ids)
    
    print("\n--- Resulting Services ---")
    for s in services:
        print(f" - {s.display_name} ({s.super_admin_service_id})")

if __name__ == "__main__":
    debug_allowed()
