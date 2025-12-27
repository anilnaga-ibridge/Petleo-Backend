import os
import django
import sys
from django.db import transaction

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription
from provider_dynamic_fields.models import (
    ProviderTemplateService, 
    ProviderTemplateCategory, 
    ProviderTemplateFacility, 
    ProviderTemplatePricing,
    ProviderCapabilityAccess
)

def fix_permissions():
    print("--- Fixing Missing Permissions ---")
    
    # 1. Get Latest User
    user = VerifiedUser.objects.order_by('-created_at').first()
    if not user:
        print("No user found.")
        return
    
    print(f"User: {user.email} ({user.auth_user_id})")
    
    # 2. Get Plan ID from Subscription
    subscription = ProviderSubscription.objects.filter(verified_user=user, is_active=True).first()
    if not subscription:
        print("No active subscription found for user.")
        # Try to find any subscription
        subscription = ProviderSubscription.objects.filter(verified_user=user).first()
        if not subscription:
            print("No subscription history found. Cannot determine Plan ID.")
            return
            
    plan_id = subscription.plan_id
    print(f"Plan ID: {plan_id}")
    
    # 3. Reconstruct Templates from Global DB
    print("Fetching global templates...")
    
    templates = {
        "services": [],
        "categories": [],
        "facilities": [],
        "pricing": []
    }
    
    # Services
    services = ProviderTemplateService.objects.all()
    for s in services:
        templates["services"].append({"id": s.super_admin_service_id})
        
    # Categories
    categories = ProviderTemplateCategory.objects.all()
    cat_service_map = {}
    for c in categories:
        cat_service_map[c.super_admin_category_id] = c.service.super_admin_service_id
        templates["categories"].append({
            "id": c.super_admin_category_id,
            "service_id": c.service.super_admin_service_id
        })
        
    # Facilities
    facilities = ProviderTemplateFacility.objects.all()
    for f in facilities:
        templates["facilities"].append({
            "id": f.super_admin_facility_id,
            "category_id": f.category.super_admin_category_id
        })
        
    # Pricing
    pricing = ProviderTemplatePricing.objects.all()
    for p in pricing:
        templates["pricing"].append({
            "id": p.super_admin_pricing_id,
            "service_id": p.service.super_admin_service_id,
            "category_id": p.category.super_admin_category_id if p.category else None,
            "facility_id": p.facility.super_admin_facility_id if p.facility else None
        })
        
    print(f"Found: {len(templates['services'])} svcs, {len(templates['categories'])} cats, {len(templates['facilities'])} facs, {len(templates['pricing'])} prices")
    
    # 4. Run Sync Logic
    print("Re-applying permissions...")
    
    try:
        with transaction.atomic():
            # Clear old permissions for this plan
            deleted_count, _ = ProviderCapabilityAccess.objects.filter(user=user, plan_id=plan_id).delete()
            print(f"Deleted {deleted_count} existing permissions for this plan.")
            
            # Also clear the mock ones I created earlier (with test-plan-123)
            ProviderCapabilityAccess.objects.filter(user=user, plan_id="test-plan-123").delete()

            perms_map = {}
            
            def add_perm(s_id, c_id, f_id, p_id, **kwargs):
                key = (s_id, c_id, f_id, p_id)
                if key not in perms_map:
                    perms_map[key] = {
                        "service_id": s_id,
                        "category_id": c_id,
                        "facility_id": f_id,
                        "pricing_id": p_id,
                        "can_view": True,
                        "can_create": False,
                        "can_edit": False,
                        "can_delete": False
                    }
                perms_map[key].update(kwargs)

            # Auto-generate from templates
            for svc in templates["services"]:
                add_perm(svc["id"], None, None, None)
                
            for cat in templates["categories"]:
                add_perm(cat["service_id"], cat["id"], None, None)
                
            for fac in templates["facilities"]:
                s_id = cat_service_map.get(fac["category_id"])
                if s_id:
                    add_perm(s_id, fac["category_id"], fac["id"], None)
                else:
                    print(f"WARNING: Could not resolve Service ID for facility {fac['id']}")

            for price in templates["pricing"]:
                add_perm(price["service_id"], price["category_id"], price["facility_id"], price["id"])

            # Create objects
            new_perms = []
            for p_data in perms_map.values():
                new_perms.append(ProviderCapabilityAccess(
                    user=user,
                    plan_id=plan_id,
                    service_id=p_data["service_id"],
                    category_id=p_data["category_id"],
                    facility_id=p_data["facility_id"],
                    pricing_id=p_data["pricing_id"],
                    can_view=p_data["can_view"],
                    can_create=p_data["can_create"],
                    can_edit=p_data["can_edit"],
                    can_delete=p_data["can_delete"],
                ))
            
            if new_perms:
                print(f"Creating {len(new_perms)} permissions...")
                ProviderCapabilityAccess.objects.bulk_create(new_perms)
                print("Permissions Created Successfully.")
            else:
                print("No permissions to create.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_permissions()
