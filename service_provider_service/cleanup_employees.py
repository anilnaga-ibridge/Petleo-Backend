import os
import django
import sys

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee

print("🔍 Scanning for VerifiedUser records that are actually Employees...")

employees = OrganizationEmployee.objects.all()
count = 0

for emp in employees:
    # Check if a VerifiedUser exists with this auth_user_id
    try:
        user = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
        print(f"⚠️ Found VerifiedUser for Employee {emp.full_name} ({emp.auth_user_id})")
        
        # Double check role
        if user.role == 'employee' or user.role is None:
            print(f"   🗑️ Deleting VerifiedUser {user.id}...")
            user.delete()
            count += 1
        else:
            print(f"   ℹ️ VerifiedUser has role '{user.role}', skipping delete (safety check).")
            
    except VerifiedUser.DoesNotExist:
        pass

print(f"✅ Cleanup complete. Deleted {count} VerifiedUser records.")
