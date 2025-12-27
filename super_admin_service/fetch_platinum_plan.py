import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from plans_coupens.models import Plan, PlanCapability
from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility
# Assuming Pricing is in dynamic_pricing
from dynamic_pricing.models import Pricing

def fetch_plan():
    print("--- Fetching Platinum Plan Details ---")
    
    plan = Plan.objects.filter(title__icontains="Platinum").first()
    if not plan:
        print("❌ Platinum Plan not found")
        return

    print(f"Plan: {plan.title} ({plan.id})")
    
    # Get Capabilities
    caps = PlanCapability.objects.filter(plan=plan)
    print(f"Found {caps.count()} capabilities.")
    
    services = {}
    categories = {}
    facilities = {}
    
    facility_category_map = {}
    
    for cap in caps:
        if cap.service:
            services[cap.service.id] = cap.service
        if cap.category:
            categories[cap.category.id] = cap.category
        if cap.facility:
            facilities[cap.facility.id] = cap.facility
            if cap.category:
                facility_category_map[cap.facility.id] = cap.category.id
            
    # Construct Payload
    payload = {
        "services": [],
        "categories": [],
        "facilities": [],
        "pricing": []
    }
    
    for s in services.values():
        payload["services"].append({
            "id": str(s.id),
            "name": s.name,
            "display_name": s.display_name,
            "icon": s.icon if hasattr(s, 'icon') else "tabler-box"
        })
        
    for c in categories.values():
        payload["categories"].append({
            "id": str(c.id),
            "service_id": str(c.service.id),
            "name": c.name
        })
        
    for f in facilities.values():
        cat_id = facility_category_map.get(f.id)
        if not cat_id:
            # Fallback: Find ANY category for this service? Or skip?
            # If facility has no category in capability, we can't sync it to Provider structure 
            # because ProviderTemplateFacility REQUIRES a category.
            print(f"⚠️ Facility {f.name} has no linked category in PlanCapability. Skipping.")
            continue
            
        payload["facilities"].append({
            "id": str(f.id),
            "category_id": str(cat_id),
            "name": f.name,
            "description": f.description
        })
        
    # Fetch Pricing Templates (if any) linked to these services
    # This might be tricky if Pricing is not directly linked to Plan in the same way.
    # But let's check if there are Pricing objects for these services.
    # Assuming Pricing model has service/category/facility FKs.
    
    all_pricing = Pricing.objects.filter(service__in=services.values())
    for p in all_pricing:
        payload["pricing"].append({
            "id": str(p.id),
            "service_id": str(p.service.id),
            "category_id": str(p.category.id) if p.category else None,
            "facility_id": str(p.facility.id) if p.facility else None,
            "price": float(p.price),
            "duration": p.duration,
            "duration": p.duration
        })

    print("\n--- JSON PAYLOAD ---")
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    fetch_plan()
