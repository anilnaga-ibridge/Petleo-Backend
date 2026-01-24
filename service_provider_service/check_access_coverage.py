
import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess

def check_coverage():
    print("Checking ProviderCapabilityAccess coverage...")
    
    # We only care about users who are PROIVDERS (Organization/Individual).
    # Employees get their permissions from Org + Role, so strict ProviderCapabilityAccess is not *directly* checked on the employee user itself (it checks the Org's).
    # However, VerifiedUser table mixes everyone.
    
    # Let's check "Individual" and "Organization" role users.
    providers = VerifiedUser.objects.filter(role__in=["individual", "organization", "serviceprovider"])
    
    total_providers = providers.count()
    print(f"Total Providers found: {total_providers}")
    
    missing_access = []
    
    for p in providers:
        # Check if they have ANY capability access records
        has_access = ProviderCapabilityAccess.objects.filter(user=p).exists()
        if not has_access:
            missing_access.append(p.email)

    if missing_access:
        print(f"⚠️ WARNING: {len(missing_access)}/{total_providers} Providers have NO `ProviderCapabilityAccess` records.")
        print(f"Affected Users: {missing_access}")
        print("These users likely have NO access in the new system.")
        print("Recommended Action: Run `sync_all_permissions.py` or re-purchase/re-sync plans.")
    else:
        print("✅ All Providers have at least one entry in `ProviderCapabilityAccess`.")

if __name__ == "__main__":
    check_coverage()
