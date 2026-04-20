import os
import sys
import django
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser
from service_provider.views import get_my_permissions
from rest_framework.test import APIRequestFactory

def diagnose_kilari():
    try:
        # Find employee
        emp = OrganizationEmployee.objects.filter(full_name__icontains="kilari").first()
        if not emp:
            print("❌ Employee Kilari not found")
            return

        print(f"👤 Found Employee: {emp.full_name}")
        print(f"🔑 Auth ID: {emp.auth_user_id}")
        print(f"🎭 Role: {emp.role}")
        print(f"🏷️ Provider Role: {emp.provider_role.name if emp.provider_role else 'None'}")

        # Simulate dynamic access fetch
        print("\n🚀 Simulating /api/provider/permissions/my-access/...")
        
        # We need to simulate the view logic
        from service_provider.models import ServiceProvider
        
        # Get final perms
        perms = emp.get_final_permissions()
        print(f"\n📊 TOTAL PERMISSIONS ({len(perms)}):")
        print(json.dumps(sorted(list(perms)), indent=2))
        
        has_create = any("VISITS_CREATE" in p for p in perms) or any("VETERINARY_VISITS_CREATE" in p for p in perms)
        print(f"\n✅ Has Create Permission: {has_create}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_kilari()
