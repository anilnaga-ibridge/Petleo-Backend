import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService, ProviderTemplateCategory

def debug_users():
    print("--- Debugging Users & Capabilities ---")
    users = VerifiedUser.objects.all()
    
    # Pre-fetch templates
    services = {s.super_admin_service_id: s.display_name for s in ProviderTemplateService.objects.all()}
    categories = {c.super_admin_category_id: c.name for c in ProviderTemplateCategory.objects.all()}
    
    print("\n--- Available Services in Templates ---")
    for s_id, s_name in services.items():
        print(f"  - {s_name} ({s_id})")

    for user in users:
        subs = ProviderSubscription.objects.filter(verified_user=user)
        if subs.count() < 2:
            continue
            
        print(f"\nUser: {user.email} (Auth ID: {user.auth_user_id})")
        print(f"  Subscriptions ({subs.count()}):")
        for sub in subs:
            print(f"    - Plan: {sub.plan_id}, Active: {sub.is_active}, End: {sub.end_date}")
            
        # Check Capabilities
        caps = ProviderCapabilityAccess.objects.filter(user=user)
        vet_caps = [c for c in caps if 'Veterinary' in services.get(c.service_id, '')]
        
        print(f"  Total Capabilities: {caps.count()}")
        print(f"  Veterinary Capabilities: {len(vet_caps)}")
        
        for cap in vet_caps:
            s_name = services.get(cap.service_id, cap.service_id)
            c_name = categories.get(cap.category_id, cap.category_id)
            print(f"    - Service: {s_name} / Category: {c_name} (View: {cap.can_view})")

if __name__ == "__main__":
    debug_users()
