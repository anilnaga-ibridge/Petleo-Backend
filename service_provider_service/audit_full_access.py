
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, AllowedService
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory, ProviderTemplateService

def audit():
    email = "nagaanil29@gmail.com"
    print(f"🕵️ Auditing FULL Access for {email}...")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        print(f"👤 User: {user.email} (Auth ID: {user.auth_user_id})")
        
        # 1. ProviderCapabilityAccess
        caps = ProviderCapabilityAccess.objects.filter(user=user)
        print(f"\n📦 ProviderCapabilityAccess ({caps.count()} records):")
        for cap in caps:
            # Resolve Service Name
            svc_name = "Unknown"
            try:
                ts = ProviderTemplateService.objects.get(super_admin_service_id=cap.service_id)
                svc_name = ts.display_name
            except: pass
            
            # Resolve Category Name
            cat_name = "Unknown"
            linked = "None"
            try:
                tc = ProviderTemplateCategory.objects.get(super_admin_category_id=cap.category_id)
                cat_name = tc.name
                linked = tc.linked_capability
            except: pass
            
            print(f"   - Service: {svc_name} ({cap.service_id}) | Cat: {cat_name} ({cap.category_id}) | Linked: {linked}")

        # 2. AllowedService
        allowed = AllowedService.objects.filter(verified_user=user)
        print(f"\n✅ AllowedService ({allowed.count()} records):")
        for a in allowed:
            print(f"   - {a.name} (Service ID: {a.service_id})")

    except VerifiedUser.DoesNotExist:
        print(f"❌ User not found.")

if __name__ == "__main__":
    audit()
