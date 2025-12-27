import os
import sys
import django
import json

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility,
    ProviderTemplatePricing,
    ProviderCapabilityAccess
)

# Mock Data
AUTH_USER_ID = "7470623a-ee4b-4922-99f5-3ce2f17171d7" # Use the existing user ID
SERVICE_ID = "711fac84-16dc-4252-b7e3-6afb7ee57c71"
CAT_ID = "e3c49920-e626-4d3d-904d-e8dbe69cb3f6"
FAC_ID = "350cf80e-eb33-4c7a-9824-276f50a4a4e7"
PRICING_ID = "pricing-123"

mock_payload = {
    "event_type": "PROVIDER.PERMISSIONS.UPDATED",
    "data": {
        "auth_user_id": AUTH_USER_ID,
        "permissions": [],
        "templates": {
            "services": [
                {
                    "id": SERVICE_ID,
                    "name": "Grooming",
                    "display_name": "Grooming Service",
                    "icon": "tabler-cut"
                }
            ],
            "categories": [
                {
                    "id": CAT_ID,
                    "service_id": SERVICE_ID,
                    "name": "Hair Cut"
                }
            ],
            "facilities": [
                {
                    "id": FAC_ID,
                    "category_id": CAT_ID,
                    "name": "Trimming",
                    "description": "Basic trim"
                }
            ],
            "pricing": [
                {
                    "id": PRICING_ID,
                    "service_id": SERVICE_ID,
                    "category_id": CAT_ID,
                    "facility_id": FAC_ID,
                    "price": "50.00",
                    "duration": 30,
                    "description": "Standard Trim"
                }
            ]
        }
    }
}

def test_sync():
    print("--- Testing Template Sync ---")
    
    data = mock_payload["data"]
    auth_user_id = data["auth_user_id"]
    templates = data["templates"]
    
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        print(f"User found: {user.full_name}")
    except VerifiedUser.DoesNotExist:
        print("User not found!")
        return

    # 1. Sync Services
    print("\nSyncing Services...")
    for svc in templates.get("services", []):
        obj, created = ProviderTemplateService.objects.update_or_create(
            super_admin_service_id=svc["id"],
            defaults={
                "name": svc["name"],
                "display_name": svc["display_name"],
                "icon": svc.get("icon", "tabler-box")
            }
        )
        print(f" - Service {obj.name} ({'Created' if created else 'Updated'})")

    # 2. Sync Categories
    print("\nSyncing Categories...")
    for cat in templates.get("categories", []):
        try:
            service_obj = ProviderTemplateService.objects.get(super_admin_service_id=cat["service_id"])
            obj, created = ProviderTemplateCategory.objects.update_or_create(
                super_admin_category_id=cat["id"],
                defaults={
                    "service": service_obj,
                    "name": cat["name"]
                }
            )
            print(f" - Category {obj.name} ({'Created' if created else 'Updated'})")
        except ProviderTemplateService.DoesNotExist:
            print(f"ERROR: Service {cat['service_id']} not found for category {cat['name']}")

    # 3. Sync Facilities
    print("\nSyncing Facilities...")
    for fac in templates.get("facilities", []):
        try:
            cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=fac["category_id"])
            obj, created = ProviderTemplateFacility.objects.update_or_create(
                super_admin_facility_id=fac["id"],
                defaults={
                    "category": cat_obj,
                    "name": fac["name"],
                    "description": fac.get("description", "")
                }
            )
            print(f" - Facility {obj.name} ({'Created' if created else 'Updated'})")
        except ProviderTemplateCategory.DoesNotExist:
            print(f"ERROR: Category {fac['category_id']} not found for facility {fac['name']}")

    # 4. Sync Pricing
    print("\nSyncing Pricing...")
    for price in templates.get("pricing", []):
        try:
            service_obj = ProviderTemplateService.objects.get(super_admin_service_id=price["service_id"])
            
            cat_obj = None
            if price.get("category_id"):
                cat_obj = ProviderTemplateCategory.objects.filter(super_admin_category_id=price["category_id"]).first()
            
            fac_obj = None
            if price.get("facility_id"):
                fac_obj = ProviderTemplateFacility.objects.filter(super_admin_facility_id=price["facility_id"]).first()

            obj, created = ProviderTemplatePricing.objects.update_or_create(
                super_admin_pricing_id=price["id"],
                defaults={
                    "service": service_obj,
                    "category": cat_obj,
                    "facility": fac_obj,
                    "price": price["price"],
                    "duration": price["duration"],
                    "description": price.get("description", "")
                }
            )
            print(f" - Pricing {obj.price} ({'Created' if created else 'Updated'})")
        except ProviderTemplateService.DoesNotExist:
             print(f"ERROR: Service {price['service_id']} not found for pricing {price['id']}")

if __name__ == "__main__":
    test_sync()
