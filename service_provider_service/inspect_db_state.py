import os
import sys
import django

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplatePricing

def inspect():
    print("--- Inspecting Permissions ---")
    users = VerifiedUser.objects.all()[:5] # Check first 5 users
    for user in users:
        print(f"User: {user.email}")
        caps = ProviderCapabilityAccess.objects.filter(user=user, pricing_id__isnull=False)
        print(f"  Priced Capabilities: {caps.count()}")
        for cap in caps:
            print(f"    - Service: {cap.service_id}, Cat: {cap.category_id}, Facility: {cap.facility_id}, Pricing: {cap.pricing_id}")
            # Check if template exists
            exists = ProviderTemplatePricing.objects.filter(super_admin_pricing_id=cap.pricing_id).exists()
            print(f"      Template Exists? {exists}")
            
if __name__ == "__main__":
    inspect()
