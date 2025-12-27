import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService, ProviderTemplateCategory, ProviderTemplateFacility

def debug_permissions():
    # emp_id = "8ef65056-e082-4e56-bc57-4bf05f93aea0" # Original emp_id
    email_to_debug = "nagaanil29@gmail.com"
    print(f"--- Debugging Permissions for User {email_to_debug} ---")
    
    try:
        user = VerifiedUser.objects.get(email=email_to_debug)
        # Assuming there's a way to get emp from user if needed, or if permissions are directly linked to VerifiedUser
        # If OrganizationEmployee is still required, you might need to find it via auth_user_id
        # emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        print(f"✅ User: {user.email}")
        
        perms = ProviderCapabilityAccess.objects.filter(user=user)
        print(f"Total Permissions: {perms.count()}")
        
        for p in perms:
            print(f"\n[Perm ID: {p.id}]")
            print(f"  Service ID: {p.service_id}")
            print(f"  Facility ID: {p.facility_id}")
            print(f"  Flags: View={p.can_view}, Create={p.can_create}, Edit={p.can_edit}, Delete={p.can_delete}")
            
            # Check Template Links
            if p.service_id:
                exists = ProviderTemplateService.objects.filter(super_admin_service_id=p.service_id).exists()
                print(f"  -> Template Service Exists? {exists}")
                if not exists:
                    print("     ⚠️ WARNING: Service Template missing!")

            if p.category_id:
                exists = ProviderTemplateCategory.objects.filter(super_admin_category_id=p.category_id).exists()
                print(f"  -> Template Category Exists? {exists}")
                if not exists:
                    print("     ⚠️ WARNING: Category Template missing!")

            if p.facility_id:
                exists = ProviderTemplateFacility.objects.filter(super_admin_facility_id=p.facility_id).exists()
                print(f"  -> Template Facility Exists? {exists}")
                if not exists:
                    print("     ⚠️ WARNING: Facility Template missing!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_permissions()
