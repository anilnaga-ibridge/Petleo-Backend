import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderCategory, ProviderFacility, ProviderTemplateCategory, ProviderTemplateFacility

SERVICE_ID = "711fac84-16dc-4252-b7e3-6afb7ee57c71"

def check_data():
    print(f"--- Checking Data for Service ID: {SERVICE_ID} ---")
    
    # Check Provider Categories
    categories = ProviderCategory.objects.filter(service_id=SERVICE_ID)
    print(f"Provider Categories found: {categories.count()}")
    for cat in categories:
        print(f" - {cat.name} (ID: {cat.id}, Active: {cat.is_active}, Provider: {cat.provider}, AuthID: {cat.provider.auth_user_id})")
        facilities = cat.facilities.all()
        print(f"   Facilities: {facilities.count()}")
        for fac in facilities:
            print(f"    - {fac.name} (Active: {fac.is_active})")

    # Check Permissions
    from provider_dynamic_fields.models import ProviderCapabilityAccess
    # Get the provider user from the first category if available
    if categories.exists():
        provider_user = categories.first().provider
        perms = ProviderCapabilityAccess.objects.filter(user=provider_user, service_id=SERVICE_ID)
        print(f"\nPermissions for user {provider_user}: {perms.count()}")
        perm_ids = []
        for p in perms:
            print(f" - CatID: {p.category_id} (View: {p.can_view})")
            if p.category_id:
                perm_ids.append(str(p.category_id))
    
    print("\n--- Checking Template Data ---")
    # Try to find ProviderTemplateService with this ID (if it's a template service ID)
    from provider_dynamic_fields.models import ProviderTemplateService
    try:
        template_service = ProviderTemplateService.objects.get(super_admin_service_id=SERVICE_ID)
        print(f"Template Service found: {template_service.display_name}")
        
        template_cats = ProviderTemplateCategory.objects.filter(service=template_service)
        print(f"Template Categories found: {template_cats.count()}")
        for cat in template_cats:
            print(f" - {cat.name} (SA_ID: {cat.super_admin_category_id})")
            if str(cat.super_admin_category_id) in perm_ids:
                print("   -> MATCHES PERMISSION")
            else:
                print("   -> NO PERMISSION MATCH")
    except ProviderTemplateService.DoesNotExist:
        print("Template Service NOT found with this ID (as super_admin_service_id).")
        
        # Try finding by ID (pk)
        try:
             template_service = ProviderTemplateService.objects.get(id=SERVICE_ID)
             print(f"Template Service found by PK: {template_service.display_name}")
        except:
             print("Template Service NOT found by PK either.")

if __name__ == "__main__":
    check_data()
