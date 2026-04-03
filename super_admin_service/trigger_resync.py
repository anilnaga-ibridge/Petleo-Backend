import os
import django
import sys
import uuid

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/super_admin_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import PurchasedPlan, ProviderPlanCapability, Plan
from plans_coupens.kafka_producer import publish_permissions_updated
from dynamic_services.models import Service
from admin_core.models import VerifiedUser

def trigger_resync(email):
    print(f"--- Triggering Sync for {email} ---")
    
    # 1. Resolve SuperAdmin User
    from admin_core.models import SuperAdmin
    user = SuperAdmin.objects.filter(auth_user_id__isnull=False).filter(
        # We know the auth_user_ids from our DB checks
        auth_user_id__in=['0992c973-9416-458a-b727-b7376b90951b', 'c800691b-5593-4c7b-95ef-096c53d8c7a5']
    ).filter(email__icontains=email.split('@')[0]).first()
    
    if not user:
        # Fallback to direct auth_user_id mapping if email filter is tricky
        if email == 'madhu@gmail.com':
            user = SuperAdmin.objects.get(auth_user_id='0992c973-9416-458a-b727-b7376b90951b')
        elif email == 'nagaanil29@gmail.com':
            user = SuperAdmin.objects.get(auth_user_id='c800691b-5593-4c7b-95ef-096c53d8c7a5')

    if not user:
        print(f"User {email} not found in SuperAdmin.")
        return

    # 2. Get Active Purchased Plans
    purchased_plans = PurchasedPlan.objects.filter(user=user, is_active=True)
    
    for pp in purchased_plans:
        plan = pp.plan
        print(f"Syncing Plan: {plan.title} for {email}")
        
        # 3. Build perms payload
        perms = ProviderPlanCapability.objects.filter(user=user, plan=plan)
        permissions_list = [
            {
                "service_id": str(p.service_id) if p.service_id else None,
                "category_id": str(p.category_id) if p.category_id else None,
                "facility_id": str(p.facility_id) if p.facility_id else None,
                "permissions": p.permissions,
                "limits": p.limits
            }
            for p in perms
        ]

        # 4. Build templates payload
        allowed_service_ids = set(p.service_id for p in perms if p.service_id)
        services = Service.objects.filter(id__in=allowed_service_ids)
        
        templates_payload = {
            "services": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "display_name": s.display_name,
                    "icon": s.icon
                } for s in services
            ],
            "categories": [],
            "facilities": [],
            "pricing": []
        }
        
        seen_categories = set()
        seen_facilities = set()
        for p in perms:
            if p.category and p.category.id not in seen_categories:
                templates_payload["categories"].append({
                    "id": str(p.category.id),
                    "service_id": str(p.category.service.id),
                    "name": p.category.name,
                    "category_key": p.category.category_key,
                })
                seen_categories.add(p.category.id)
            if p.facility and p.facility.id not in seen_facilities:
                templates_payload["facilities"].append({
                    "id": str(p.facility.id),
                    "category_id": str(p.category.id) if p.category else None, 
                    "name": p.facility.name,
                    "description": p.facility.description
                })
                seen_facilities.add(p.facility.id)

        # 5. Dynamic Caps
        from dynamic_permissions.models import PlanCapability as DynPlanCapability
        dynamic_caps_payload = []
        dyn_caps = DynPlanCapability.objects.filter(plan=plan)
        for dc in dyn_caps:
            modules = dc.capability.modules.filter(is_active=True).values('key', 'name', 'route', 'icon', 'sequence')
            dynamic_caps_payload.append({
                "capability_key": dc.capability.key,
                "modules": list(modules)
            })

        purchased_plan_data = {
            "plan_id": str(plan.id),
            "plan_title": plan.title,
            "billing_cycle": pp.billing_cycle,
            "start_date": pp.start_date.isoformat() if pp.start_date else None,
            "end_date": pp.end_date.isoformat() if pp.end_date else None,
            "is_active": pp.is_active
        }

        # 6. Publish
        publish_permissions_updated(
            auth_user_id=str(user.auth_user_id),
            purchase_id=str(pp.id),
            permissions_list=permissions_list,
            purchased_plan=purchased_plan_data,
            templates=templates_payload,
            dynamic_capabilities=dynamic_caps_payload
        )
        print(f"Successfully published updated event for {email}")

if __name__ == "__main__":
    trigger_resync('madhu@gmail.com')
    trigger_resync('nagaanil29@gmail.com')
