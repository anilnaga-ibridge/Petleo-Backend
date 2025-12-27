import os
import django
from django.http import HttpRequest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility
)
from service_provider.views import get_my_permissions

def verify_post_purchase():
    print("--- Verifying Post-Purchase State ---")
    
    email = 'nagaanil29@gmail.com'
    user = VerifiedUser.objects.filter(email=email).first()
    if not user:
        print(f"User {email} not found")
        return

    print(f"User: {user.email}")
    
    # 1. Check Capabilities (The raw permissions)
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    print(f"\n[DB] Total Capability Records: {caps.count()}")
    
    if caps.count() == 0:
        print("❌ NO CAPABILITIES FOUND. Kafka Sync likely failed or hasn't run.")
        return

    # 2. Check Templates (The structure)
    services = ProviderTemplateService.objects.all()
    print(f"[DB] Total Template Services: {services.count()}")
    
    if services.count() == 0:
        print("❌ NO TEMPLATES FOUND. Kafka Sync failed to save templates.")
        return

    # 3. Check API Output (The logic)
    print("\n[API] checking get_my_permissions output...")
    
    # Mock Request
    class MockUser:
        def __init__(self, real_user):
            self.real_user = real_user
            self.is_authenticated = True
            self.email = real_user.email
            self.capabilities = real_user.capabilities
            
    request = HttpRequest()
    request.method = 'GET'
    request.user = MockUser(user)
    
    try:
        response = get_my_permissions(request)
        perms = response.data.get('permissions', [])
        print(f"API returned {len(perms)} services.")
        
        for svc in perms:
            print(f" - {svc['service_name']} (View: {svc['can_view']})")
            for cat in svc.get('categories', []):
                print(f"   -> Category: {cat['name']} (View: {cat['can_view']})")
                
    except Exception as e:
        print(f"❌ API Logic Failed: {e}")

if __name__ == "__main__":
    verify_post_purchase()
