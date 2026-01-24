
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory

TARGET_EMAIL = "nagaanil29@gmail.com"

def debug_links():
    print(f"🔍 Checking Template Links for {TARGET_EMAIL}...")
    
    try:
        user = VerifiedUser.objects.get(email=TARGET_EMAIL)
    except VerifiedUser.DoesNotExist:
        print("User not found")
        return

    # Get all categories assigned to this user via ProviderCapabilityAccess
    cat_ids = ProviderCapabilityAccess.objects.filter(user=user, category_id__isnull=False).values_list('category_id', flat=True)
    
    print(f"📦 Found {len(cat_ids)} assigned categories in Permission Table.")
    
    cats = ProviderTemplateCategory.objects.filter(super_admin_category_id__in=cat_ids)
    
    print(f"📄 Found {cats.count()} matching Template Categories.")
    
    for c in cats:
        print(f"   - Name: {c.name:<30} | ID: {c.super_admin_category_id} | Linked Cap: {c.linked_capability}")

if __name__ == "__main__":
    debug_links()
