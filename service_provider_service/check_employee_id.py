import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider

def check_employee():
    emp_id = "8ef65056-e082-4e56-bc57-4bf05f93aea0"
    print(f"--- Checking Employee ID: {emp_id} ---")
    
    try:
        emp = OrganizationEmployee.objects.get(id=emp_id)
        print(f"✅ Found Employee: {emp.full_name} ({emp.email})")
        print(f"   Auth ID: {emp.auth_user_id}")
        print(f"   Organization: {emp.organization.verified_user.email}")
        print(f"   Status: {emp.status}")
        
        # Check VerifiedUser
        from service_provider.models import VerifiedUser
        try:
            vu = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
            print(f"✅ Found VerifiedUser for Employee: {vu.email}")
        except VerifiedUser.DoesNotExist:
            print("❌ VerifiedUser NOT FOUND for Employee! This is the cause of the 404.")
            
    except OrganizationEmployee.DoesNotExist:
        print("❌ Employee NOT FOUND in database.")
        
        # Check if it exists as an Auth User ID?
        # Sometimes frontend sends Auth ID instead of Employee ID
        try:
            emp_by_auth = OrganizationEmployee.objects.get(auth_user_id=emp_id)
            print(f"⚠️ Found as Auth User ID! Employee ID is: {emp_by_auth.id}")
        except OrganizationEmployee.DoesNotExist:
            print("❌ Not found as Auth User ID either.")

if __name__ == "__main__":
    check_employee()
