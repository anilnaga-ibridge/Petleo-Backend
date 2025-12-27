import os
import django
import sys
from django.conf import settings

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderCapabilityAccess
)

def debug_view_logic():
    print("--- Debugging View Logic ---")
    
    # 1. Get User
    user = VerifiedUser.objects.order_by('-created_at').first()
    print(f"User: {user.email}")
    
    # 2. Target Service ID (from previous inspection)
    # Training Service
    service_id = "d0de4652-d2e7-4cab-ae09-05999f365eed" 
    print(f"Target Service ID: {service_id}")
    
    # 3. Simulate Template Fetching
    print("\n--- Fetching Templates ---")
    template_data = []
    try:
        template_service = ProviderTemplateService.objects.get(super_admin_service_id=service_id)
        print(f"Found Service: {template_service.name}")
        
        templates = ProviderTemplateCategory.objects.filter(service=template_service)
        print(f"Found {templates.count()} template categories.")
        
        for t in templates:
            print(f" - {t.name} (ID: {t.super_admin_category_id})")
            template_data.append({
                "id": f"TEMPLATE_{t.id}",
                "original_id": t.super_admin_category_id,
                "name": t.name
            })
            
    except ProviderTemplateService.DoesNotExist:
        print("❌ ProviderTemplateService NOT FOUND for this ID.")
    except Exception as e:
        print(f"❌ Error fetching templates: {e}")

    # 4. Simulate Permission Injection
    print("\n--- Checking Permissions ---")
    perms = ProviderCapabilityAccess.objects.filter(user=user)
    perms = perms.filter(service_id=service_id)
    print(f"Found {perms.count()} permissions for this service.")
    
    perm_map = {}
    service_level_perms = []
    
    for p in perms:
        if p.category_id:
            cid = str(p.category_id)
            if cid not in perm_map:
                perm_map[cid] = []
            perm_map[cid].append(p)
            print(f" - Cat Perm: {cid} (View: {p.can_view})")
        elif p.service_id and not p.category_id and not p.facility_id:
            service_level_perms.append(p)
            print(f" - Service Perm: {p.service_id} (View: {p.can_view})")

    # 5. Final Result Simulation
    print("\n--- Final Result ---")
    for item in template_data:
        c_id = str(item.get("original_id"))
        category_perms = perm_map.get(c_id, []) + service_level_perms
        
        can_view = False
        for p in category_perms:
            if p.can_view: can_view = True
            
        print(f"Category: {item['name']} -> Can View: {can_view}")

if __name__ == "__main__":
    debug_view_logic()
