
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from dynamic_services.models import Service
from dynamic_categories.models import Category
from plans_coupens.models import Plan, PlanCapability

# 1. Find VETERINARY_CORE Service
svc = Service.objects.filter(name__iexact="VETERINARY_CORE").first()
if not svc:
    print("CRITICAL: VETERINARY_CORE service not found (even after rename).")
    # Fallback check
    svc = Service.objects.filter(name__iexact="VETERINARY").first()
    if svc: print(f"Found it as {svc.name} instead.")

if svc:
    print(f"Service: {svc.name} (ID: {svc.id})")
    
    # 2. List Categories
    cats = Category.objects.filter(service=svc)
    print(f"Categories ({cats.count()}):")
    for c in cats:
        print(f"  - {c.name} (Key: {c.category_key if hasattr(c, 'category_key') else 'NoKey'})")

    # 3. Check Gold Plan Permissions
    plan = Plan.objects.filter(title__icontains="Gold").first()
    if plan:
        print(f"\nPlan: {plan.title}")
        caps = PlanCapability.objects.filter(plan=plan, service=svc)
        if not caps.exists():
            print("  No capabilities found for VETERINARY_CORE in this plan.")
        for cap in caps:
            cat_name = cap.category.name if cap.category else "All Categories"
            print(f"  - Category: {cat_name}")
            print(f"    Permissions: {cap.permissions}")
    else:
        print("Gold Plan not found.")
