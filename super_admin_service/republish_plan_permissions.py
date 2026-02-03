
import os
import sys
import django
import argparse
import logging

# Setup Django for Super Admin Service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import PurchasedPlan, Plan
# from plans_coupens.purchase_publish_wrapper import purchase_publish_wrapper # Removed bad import
from plans_coupens.models import ProviderPlanCapability
from plans_coupens.kafka_producer import publish_permissions_updated
# We might need to manually build the payload if we don't want to create a new purchase.
# purchase_publish_wrapper does both. We just want the publishing part.
# Let's verify existing logic in purchase_publish_wrapper to extract the build step.

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def republish_permissions(email, dry_run=True):
    logger.info(f"🔎 Looking for active plans for: {email}")
    
    # 1. Find the User (We might need Auth service or just trust the email exists in PurchasedPlan links if we had a User model here)
    # PurchasedPlan links to 'user' which is likely a generic User object or Auth User.
    # We can filter `PurchasedPlan.objects.exclude(is_active=False)` and try to match email if possible.
    # Wait, PurchasedPlan.user might be an object or ID.
    # In `purchase_publish_wrapper.py`: `PurchasedPlan.objects.create(user=user...)`
    # We need to know how `user` is stored. UUID? Or Object?
    
    # Let's indiscriminately check all purchased plans and filter by email if we can inspect the user object.
    
    plans = PurchasedPlan.objects.filter(is_active=True)
    
    found = False
    for pp in plans:
        # Check user email
        u = pp.user
        u_email = getattr(u, 'email', None)
        if hasattr(u, 'username'): u_email = u.username 
        # Adapt based on actual User model in Super Admin
        
        if u_email != email:
            continue
            
        found = True
        logger.info(f"✅ Found Active Plan: {pp.plan.title} (ID: {pp.plan.id})")
        
        if dry_run:
            logger.info("⚠️  DRY RUN: Would publish permissions for this plan.")
            # We can try to build the payload to show what would be sent
            payload = build_payload_for_plan(pp)
            logger.info(f"📦 Payload Preview: {len(payload)} items")
        else:
            logger.info("🔄 Publishing Kafka Event...")
            # Re-use logic to build and send
            payload = build_payload_for_plan(pp)
            
            # We need templates too
            templates = build_templates_for_plan(pp)
            
            # Push
            # Auth User ID extraction
            auth_id = str(u.auth_user_id) if hasattr(u, 'auth_user_id') else str(u.id)
            
            plan_info = {
                "id": str(pp.id),
                "plan_id": str(pp.plan.id),
                "billing_cycle_id": pp.billing_cycle if pp.billing_cycle else None,
                "start_date": pp.start_date.isoformat(),
                "end_date": pp.end_date.isoformat() if pp.end_date else None,
            }
            
            publish_permissions_updated(auth_id, str(pp.id), payload, plan_info, templates=templates)
            logger.info("✅ Event Published.")

    if not found:
        logger.warning(f"❌ No active plan found for {email}")

def build_payload_for_plan(purchased_plan):
    user = purchased_plan.user
    plan = purchased_plan.plan
    
    perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)
    payload = []
    
    for p in perms:
        payload.append({
            "plan_id": str(p.plan.id),
            "service_id": str(p.service.id) if p.service else None,
            "service_name": getattr(p.service, "display_name", None),
            "category_id": str(p.category.id) if p.category else None,
            "category_name": getattr(p.category, "name", None),
            "facility_id": str(p.facility.id) if p.facility else None,
            "facility_name": getattr(p.facility, "name", None),
            "can_view": bool(p.permissions.get("can_view", True)),
            "can_create": bool(p.permissions.get("can_create", False)),
            "can_edit": bool(p.permissions.get("can_edit", False)),
            "can_delete": bool(p.permissions.get("can_delete", False)),
        })
    return payload

def build_templates_for_plan(purchased_plan):
    user = purchased_plan.user
    plan = purchased_plan.plan
    perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)
    
    templates = {
        "services": [], "categories": [], "facilities": [], "pricing": []
    }
    seen_services = set()
    seen_categories = set()
    seen_facilities = set()
    
    # 1. Services
    for p in perms:
         if p.service and p.service.id not in seen_services:
            templates["services"].append({
                "id": str(p.service.id),
                "name": p.service.name,
                "display_name": p.service.display_name,
                "icon": getattr(p.service, "icon", "tabler-box") or "tabler-box"
            })
            seen_services.add(p.service.id)
            
    # 2. Categories
    from dynamic_categories.models import Category
    from dynamic_facilities.models import Facility
    from dynamic_pricing.models import PricingRule

    all_cats = Category.objects.filter(service__id__in=seen_services)
    for cat in all_cats:
        if cat.id not in seen_categories:
            templates["categories"].append({
                "id": str(cat.id),
                "service_id": str(cat.service.id),
                "name": cat.name,
                "linked_capability": cat.linked_capability
            })
            seen_categories.add(cat.id)

    # 3. Facilities
    all_facs = Facility.objects.filter(category__service__id__in=seen_services)
    print(f"DEBUG: Found {all_facs.count()} facilities for services {seen_services}")
    for fac in all_facs:
        if fac.id not in seen_facilities:
            templates["facilities"].append({
                "id": str(fac.id),
                "category_id": str(fac.category.id),
                "name": fac.name,
                "description": getattr(fac, "description", "")
            })
            seen_facilities.add(fac.id)
            print(f"DEBUG: Added facility template: {fac.name} (Cat: {fac.category.name})")

    # 4. Pricing
    pricing_qs = PricingRule.objects.filter(service__id__in=seen_services, is_active=True)
    for price in pricing_qs:
        p_cat_id = str(price.category.id) if price.category else None
        p_fac_id = str(price.facility.id) if price.facility else None
        
        # Infer category from facility if missing
        if p_fac_id and not p_cat_id and price.facility.category:
            p_cat_id = str(price.facility.category.id)
        
        include_price = False
        if not p_cat_id and not p_fac_id:
            include_price = True
        elif p_cat_id and not p_fac_id:
            if price.category.id in seen_categories:
                include_price = True
        elif p_fac_id:
            if price.facility.id in seen_facilities:
                include_price = True
        
        if include_price:
            templates["pricing"].append({
                "id": str(price.id),
                "service_id": str(price.service.id),
                "category_id": p_cat_id,
                "facility_id": p_fac_id,
                "price": str(price.base_price),
                "duration": price.duration_minutes,
                "description": f"Default pricing for {price.service.display_name}"
            })
    
    return templates

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="User email to sync", default=None)
    parser.add_argument("--run", action="store_true", help="Execute sync")
    args = parser.parse_args()
    
    if args.email:
         republish_permissions(args.email, dry_run=not args.run)
    else:
         print("Listing ALL Active Plans...")
         # Call with dummy or logic to list all
         # We need to expose list logic.
         # For quick hack, let's just do it here:
         plans = PurchasedPlan.objects.filter(is_active=True)
         for pp in plans:
             u = pp.user
             email = getattr(u, 'email', getattr(u, 'username', 'Unknown'))
             print(f"Plan: {pp.plan.title} | User: {email} | ID: {pp.id}")
