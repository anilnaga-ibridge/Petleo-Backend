import os
import sys
import django

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderCapabilityAccess
)

SERVICE_ID = "711fac84-16dc-4252-b7e3-6afb7ee57c71" # The service ID from the issue

def inspect_data():
    print(f"--- Inspecting Data for Service {SERVICE_ID} ---")
    
    # 1. Check Template Service
    try:
        ts = ProviderTemplateService.objects.get(super_admin_service_id=SERVICE_ID)
        print(f"Template Service Found: {ts.name} (ID: {ts.id})")
    except ProviderTemplateService.DoesNotExist:
        print("Template Service NOT found!")
        return

    # 2. Check Template Categories
    cats = ProviderTemplateCategory.objects.filter(service=ts)
    print(f"Template Categories: {cats.count()}")
    for c in cats:
        print(f" - {c.name} (Original ID: {c.super_admin_category_id})")

    # 3. Check Permissions for Users
    print("\n--- Checking Permissions ---")
    perms = ProviderCapabilityAccess.objects.filter(service_id=SERVICE_ID)
    print(f"Total Permissions for this Service: {perms.count()}")
    
    for p in perms:
        u_name = p.user.full_name if p.user else "Unknown"
        c_id = p.category_id if p.category_id else "ALL (Service Level)"
        print(f" User: {u_name} | Cat: {c_id} | View: {p.can_view}")

if __name__ == "__main__":
    inspect_data()
