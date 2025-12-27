import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility,
    ProviderTemplatePricing
)

def debug_data():
    print("--- Debugging Provider Data ---")
    
    # 1. Find the Provider User
    # We'll look for the user from previous tests or just the first one with capabilities
    user = VerifiedUser.objects.filter(email='ram@gmail.com').first()
    if not user:
        print("User ram@gmail.com not found. searching for any user with capabilities...")
        user = VerifiedUser.objects.filter(capabilities__isnull=False).distinct().first()
    
    if not user:
        print("No user with capabilities found.")
        return

    print(f"User: {user.email} (ID: {user.auth_user_id})")

    # 2. Check Capabilities
    perms = ProviderCapabilityAccess.objects.filter(user=user)
    print(f"\nTotal Permissions: {perms.count()}")
    
    services_seen = set()
    categories_seen = set()
    facilities_seen = set()

    for p in perms:
        services_seen.add(p.service_id)
        if p.category_id: categories_seen.add(p.category_id)
        if p.facility_id: facilities_seen.add(p.facility_id)
        
        # Print detail if it looks like one of the missing ones
        # Just print all for now if count is small, or summary
    
    print(f"Unique Services: {len(services_seen)}")
    print(f"Unique Categories: {len(categories_seen)}")
    print(f"Unique Facilities: {len(facilities_seen)}")

    # 3. Check Templates for these IDs
    print("\n--- Template Check ---")
    
    for s_id in services_seen:
        try:
            svc = ProviderTemplateService.objects.get(super_admin_service_id=s_id)
            print(f"Service Found: {svc.display_name} ({s_id})")
            
            # Check categories for this service in DB
            db_cats = ProviderTemplateCategory.objects.filter(service=svc)
            print(f"  - DB Categories: {db_cats.count()}")
            for c in db_cats:
                print(f"    - {c.name} ({c.super_admin_category_id})")
                
        except ProviderTemplateService.DoesNotExist:
            print(f"MISSING TEMPLATE for Service ID: {s_id}")

    # Check specifically for "Training"
    print("\n--- Checking for 'Training' Service ---")
    training_svc = ProviderTemplateService.objects.filter(display_name__icontains="Training").first()
    if training_svc:
        print(f"Found Training Service: {training_svc.display_name} ({training_svc.super_admin_service_id})")
        # Check categories
        cats = ProviderTemplateCategory.objects.filter(service=training_svc)
        for c in cats:
            print(f"  - Category: {c.name}")
    else:
        print("Training Service Template NOT FOUND.")

    print("\n--- Detailed Permission Dump ---")
    for p in perms:
        s_name = "Unknown"
        c_name = "None"
        f_name = "None"
        
        if p.service_id:
            s = ProviderTemplateService.objects.filter(super_admin_service_id=p.service_id).first()
            if s: s_name = s.display_name
            
        if p.category_id:
            c = ProviderTemplateCategory.objects.filter(super_admin_category_id=p.category_id).first()
            if c: c_name = c.name
            
        if p.facility_id:
            f = ProviderTemplateFacility.objects.filter(super_admin_facility_id=p.facility_id).first()
            if f: f_name = f.name
            
        print(f"[{s_name}] -> [{c_name}] -> [{f_name}] (View: {p.can_view})")

if __name__ == "__main__":
    debug_data()
