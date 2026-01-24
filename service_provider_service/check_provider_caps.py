
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory, ProviderTemplateService

def check_caps():
    email = "nagaanil29@gmail.com"
    print(f"🔍 Checking Provider Capabilities for {email}...")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        print(f"👤 User: {user.email} (ID: {user.id})")
        
        # Check ProviderCapabilityAccess
        caps = ProviderCapabilityAccess.objects.filter(user=user)
        print(f"🔢 Total Assigned Capabilities: {caps.count()}")
        
        print("\n--- Assigned Categories/Keys ---")
        for cap in caps:
            cat_name = "Unknown"
            linked = "None"
            
            if cap.category_id:
                try:
                    tmpl = ProviderTemplateCategory.objects.get(super_admin_category_id=cap.category_id)
                    cat_name = tmpl.name
                    linked = tmpl.linked_capability
                except ProviderTemplateCategory.DoesNotExist:
                    cat_name = f"Orphaned ID: {cap.category_id}"
            
            print(f"   - Category: {cat_name} | Linked Key: {linked}")
            
        # Check what get_all_plan_capabilities returns
        print("\n--- Calculated Plan Capabilities (get_all_plan_capabilities) ---")
        param_caps = user.get_all_plan_capabilities()
        print(f"   Keys: {sorted(list(param_caps))}")

    except VerifiedUser.DoesNotExist:
        print(f"❌ User {email} not found.")

if __name__ == "__main__":
    check_caps()
