
import os
import django
from django.conf import settings

# Setup Django FIRST before any other imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

# Override ALLOWED_HOSTS for testing
settings.ALLOWED_HOSTS = ['*']

import json
import uuid
from django.utils import timezone
from rest_framework.test import APIClient
from django.urls import reverse
from plans_coupens.models import Plan, BillingCycleConfig
from admin_core.models import SuperAdmin

def test_plan_inactivation_logic():
    client = APIClient()
    
    # 1. Create a Super Admin user for authentication
    admin_user, _ = SuperAdmin.objects.get_or_create(
        email="testadmin@example.com", 
        defaults={
            "first_name": "Test",
            "last_name": "Admin",
            "is_staff": True, 
            "is_super_admin": True,
            "auth_user_id": uuid.uuid4()
        }
    )
    client.force_authenticate(user=admin_user)
    
    # 2. Create a test plan
    billing_cycle, _ = BillingCycleConfig.objects.get_or_create(code="MONTHLY", defaults={"display_name": "Monthly", "duration_days": 30})
    plan = Plan.objects.create(
        title="Test Inactivation Plan",
        target_type="INDIVIDUAL",
        billing_cycle=billing_cycle,
        is_active=True
    )
    print(f"✅ Created Plan: {plan.title} (ID: {plan.id}, Active: {plan.is_active})")
    
    # 3. Test Inactivation via API (Patch)
    url = f"/api/superadmin/plans/{plan.id}/"
    response = client.patch(url, {"is_active": False}, format='json')
    
    if response.status_code == 200:
        plan.refresh_from_db()
        print(f"✅ Inactivated Plan via API. New Status: {plan.is_active}")
    else:
        content = getattr(response, 'data', response.content)
        print(f"❌ Failed to inactivate plan: {response.status_code} - {content}")
        return

    # 4. Test Purchase Blocking
    purchase_url = "/api/superadmin/purchase/"
    
    purchase_payload = {
        "plan_id": str(plan.id),
        "billing_cycle_id": str(billing_cycle.id)
    }
    
    response = client.post(purchase_url, purchase_payload, format='json')
    
    if response.status_code == 400:
        data = getattr(response, 'data', json.loads(response.content))
        if "no longer available" in str(data):
            print(f"✅ Purchase Blocked as expected: {data.get('detail')}")
        else:
            print(f"❌ Purchase blocked but with unexpected message: {data}")
    else:
        content = getattr(response, 'data', response.content)
        print(f"❌ Purchase NOT blocked or unexpected error: {response.status_code} - {content}")

if __name__ == "__main__":
    test_plan_inactivation_logic()
