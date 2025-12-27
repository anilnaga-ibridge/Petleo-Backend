import os
import sys
import django

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/super_admin_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from plans_coupens.models import Plan, ProviderPlanCapability
from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility

def inspect_plan_capabilities(plan_name_fragment):
    print(f"--- Inspecting Plan Capabilities for '{plan_name_fragment}' ---")
    
    plans = Plan.objects.filter(title__icontains=plan_name_fragment)
    if not plans.exists():
        print("No plan found.")
        return
        
    for plan in plans:
        print(f"\nPlan: {plan.title} (ID: {plan.id})")
        caps = ProviderPlanCapability.objects.filter(plan=plan)
        print(f"Capabilities found: {caps.count()}")
        
        for cap in caps:
            s_name = cap.service.display_name if cap.service else "None"
            c_name = cap.category.name if cap.category else "None"
            f_name = cap.facility.name if cap.facility else "None"
            print(f" - Service: {s_name}, Category: {c_name}, Facility: {f_name}")
            print(f"   Permissions: View={cap.can_view}, Create={cap.can_create}, Edit={cap.can_edit}, Delete={cap.can_delete}")

            # Check if this service has children that are NOT in capabilities
            if cap.service and not cap.category:
                print(f"   -> Service Level Capability. Checking children...")
                cats = Category.objects.filter(service=cap.service)
                print(f"      Found {cats.count()} categories for service {s_name}")
                for c in cats:
                    print(f"      - {c.name}")

if __name__ == "__main__":
    # Replace with a plan name likely to be used, e.g., "Gold", "Basic", or just list all
    inspect_plan_capabilities("") 
