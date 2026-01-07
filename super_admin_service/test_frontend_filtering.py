
import os
import django

# Setup Django FIRST before any other imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from rest_framework.test import APIClient
from plans_coupens.models import Plan, BillingCycleConfig

def test_frontend_filtering():
    client = APIClient()
    
    # 1. Create an active and an inactive plan
    billing_cycle, _ = BillingCycleConfig.objects.get_or_create(code="MONTHLY", defaults={"display_name": "Monthly", "duration_days": 30})
    
    active_plan = Plan.objects.create(
        title="Active Plan",
        target_type="INDIVIDUAL",
        billing_cycle=billing_cycle,
        is_active=True
    )
    
    inactive_plan = Plan.objects.create(
        title="Inactive Plan",
        target_type="INDIVIDUAL",
        billing_cycle=billing_cycle,
        is_active=False
    )
    
    print(f"✅ Created Active Plan: {active_plan.id}")
    print(f"✅ Created Inactive Plan: {inactive_plan.id}")
    
    # 2. Fetch plans via ProviderPlanView (Frontend API)
    url = "/api/superadmin/provider/plans/"
    response = client.get(url, {"role": "individual"})
    
    if response.status_code == 200:
        data = response.data
        if isinstance(data, dict):
            plans = data.get('results', [])
        else:
            plans = data
            
        plan_ids = [str(p['id']) for p in plans]
        
        print(f"🔍 Received {len(plan_ids)} plans from API")
        
        if str(active_plan.id) in plan_ids and str(inactive_plan.id) not in plan_ids:
            print("✅ Frontend Filtering Success: Active plan is present, Inactive plan is hidden.")
        else:
            print(f"❌ Frontend Filtering Failure: Active in list? {str(active_plan.id) in plan_ids}, Inactive in list? {str(inactive_plan.id) in plan_ids}")
    else:
        print(f"❌ API Request Failed: {response.status_code}")

if __name__ == "__main__":
    test_frontend_filtering()
