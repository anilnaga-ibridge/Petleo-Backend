
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory

def cleanup_caps():
    email = "nagaanil29@gmail.com"
    print(f"🧹 Cleaning up capabilities for {email}...")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        
        # List all templates to find correct names
        all_tmpls = ProviderTemplateCategory.objects.all()
        print("📋 Available Templates:")
        for t in all_tmpls:
            print(f"   - {t.name} (ID: {t.super_admin_category_id})")

        cats_to_remove = [
            "Puppy Day Care", 
            "Small Breed Dog Day Care", 
            "Behavioral Training", 
            "Daily Training"
        ]
        
        for name in cats_to_remove:
            print(f"   Searching for {name} capability...")
            # Find template first to get ID
            tmpl = ProviderTemplateCategory.objects.filter(name__iexact=name).first()
            if tmpl:
                print(f"   Found Template ID: {tmpl.super_admin_category_id}")
                
                deleted_count, _ = ProviderCapabilityAccess.objects.filter(
                    user=user, 
                    category_id=tmpl.super_admin_category_id
                ).delete()
                
                print(f"   🗑️ Deleted {deleted_count} records for {name}.")
            else:
                print(f"   ⚠️ Template for {name} not found.")

    except VerifiedUser.DoesNotExist:
        print(f"❌ User {email} not found.")

if __name__ == "__main__":
    cleanup_caps()
