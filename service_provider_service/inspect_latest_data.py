import os
import django
import sys
from django.conf import settings

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import (
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility, 
    ProviderTemplatePricing,
    ProviderCapabilityAccess
)
from service_provider.models import VerifiedUser

def inspect_latest_provider_data():
    print("--- Inspecting Latest Provider Data ---")
    
    # Get the most recently created user (likely the new provider)
    latest_user = VerifiedUser.objects.order_by('-created_at').first()
    if not latest_user:
        print("No users found.")
        return

    print(f"Latest User: {latest_user.email} (Auth ID: {latest_user.auth_user_id})")
    
    # Check Capabilities
    capabilities = ProviderCapabilityAccess.objects.filter(user__auth_user_id=latest_user.auth_user_id)
    print(f"\nProvider Capabilities ({capabilities.count()}):")
    for cap in capabilities:
        print(f" - Plan: {cap.plan_id}, Service: {cap.service_id}, Category: {cap.category_id}, Facility: {cap.facility_id}")

    # Check Template Data (Global)
    print(f"\n--- Global Template Data ---")
    services = ProviderTemplateService.objects.all()
    print(f"Template Services ({services.count()}):")
    for s in services:
        print(f" - {s.name} (SA ID: {s.super_admin_service_id})")
        
        categories = ProviderTemplateCategory.objects.filter(service=s)
        print(f"   - Categories ({categories.count()}):")
        for c in categories:
            print(f"     - {c.name} (SA ID: {c.super_admin_category_id})")
            
            facilities = ProviderTemplateFacility.objects.filter(category=c)
            print(f"       - Facilities ({facilities.count()}):")
            for f in facilities:
                print(f"         - {f.name} (SA ID: {f.super_admin_facility_id})")
                
        pricing = ProviderTemplatePricing.objects.filter(service=s)
        print(f"   - Pricing Rules ({pricing.count()}):")
        for p in pricing:
            print(f"     - {p.price} (Cat: {p.category.name if p.category else 'None'})")

if __name__ == "__main__":
    inspect_latest_provider_data()
