import os
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, AllowedService
from provider_dynamic_fields.models import ProviderTemplateService

def debug_lookup():
    print("--- Debugging UUID vs String Lookup ---")
    
    email = 'nagaanil29@gmail.com'
    user = VerifiedUser.objects.filter(email=email).first()
    if not user:
        print("User not found")
        return

    # 1. Get IDs from AllowedService (UUIDs)
    allowed_uuids = set(AllowedService.objects.filter(verified_user=user).values_list('service_id', flat=True))
    print(f"Allowed UUIDs (Count: {len(allowed_uuids)}):")
    for uid in allowed_uuids:
        print(f" - {uid} (Type: {type(uid)})")

    # 2. Try filtering ProviderTemplateService (CharField) using these UUIDs
    print("\nAttempting filter(super_admin_service_id__in=allowed_uuids)...")
    services = ProviderTemplateService.objects.filter(super_admin_service_id__in=allowed_uuids)
    print(f"Found Services: {services.count()}")
    for s in services:
        print(f" - {s.display_name}")

    # 3. Try converting to strings
    allowed_strs = {str(uid) for uid in allowed_uuids}
    print("\nAttempting filter(super_admin_service_id__in=allowed_strs)...")
    services_str = ProviderTemplateService.objects.filter(super_admin_service_id__in=allowed_strs)
    print(f"Found Services (Strings): {services_str.count()}")
    for s in services_str:
        print(f" - {s.display_name}")

if __name__ == "__main__":
    debug_lookup()
