import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import ProviderPlanCapability, PurchasedPlan
from django.contrib.auth import get_user_model

User = get_user_model()

def debug_org_permissions():
    email = "nagaanil29@gmail.com"
    print(f"--- Debugging ProviderPlanCapability for {email} in SuperAdmin ---")
    
    try:
        user = User.objects.get(email=email)
        print(f"✅ User: {user.email} (ID: {user.id})")
        
        perms = ProviderPlanCapability.objects.filter(user=user)
        print(f"Found {perms.count()} permission records.")
        
        for p in perms:
            print(f"\n[Perm ID: {p.id}]")
            print(f"  Service: {p.service.display_name if p.service else 'None'}")
            print(f"  Category: {p.category.name if p.category else 'None'}")
            print(f"  Facility: {p.facility.name if p.facility else 'None'}")
            print(f"  Flags: View={p.can_view}, Create={p.can_create}, Edit={p.can_edit}, Delete={p.can_delete}")

    except User.DoesNotExist:
        print(f"❌ User {email} not found in SuperAdmin DB")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_org_permissions()
