
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, AllowedService
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService

def wipe():
    email = "nagaanil29@gmail.com"
    print(f"🧹 Wiping extraneous access for {email}...")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        
        # We only want to KEEP these Service IDs (from Basic Plan)
        # Grooming: 711fac84-16dc-4252-b7e3-6afb7ee57c71
        # Veterinary Management: 2dff446f-c95f-4310-ba4d-05e3395dd7eb
        
        valid_service_ids = [
            "711fac84-16dc-4252-b7e3-6afb7ee57c71",
            "2dff446f-c95f-4310-ba4d-05e3395dd7eb"
        ]
        
        # 1. Clean ProviderCapabilityAccess
        all_caps = ProviderCapabilityAccess.objects.filter(user=user)
        to_delete_caps = all_caps.exclude(service_id__in=valid_service_ids)
        count_caps = to_delete_caps.count()
        to_delete_caps.delete()
        print(f"   🗑️ Deleted {count_caps} ProviderCapabilityAccess records.")
        
        # 2. Clean AllowedService
        all_allowed = AllowedService.objects.filter(verified_user=user)
        to_delete_allowed = all_allowed.exclude(service_id__in=valid_service_ids)
        count_allowed = to_delete_allowed.count()
        to_delete_allowed.delete()
        print(f"   🗑️ Deleted {count_allowed} AllowedService records.")
        
        print("\n✅ Cleanup Complete.")

    except VerifiedUser.DoesNotExist:
        print(f"❌ User not found.")

if __name__ == "__main__":
    wipe()
