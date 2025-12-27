import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee

def fix_employee_user():
    emp_id = "8ef65056-e082-4e56-bc57-4bf05f93aea0"
    print(f"--- Fixing Missing VerifiedUser for Employee {emp_id} ---")
    
    try:
        emp = OrganizationEmployee.objects.get(id=emp_id)
        print(f"✅ Found Employee: {emp.full_name}")
        print(f"   Auth ID: {emp.auth_user_id}")
        
        # Check if VerifiedUser exists
        try:
            vu = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
            print(f"✅ VerifiedUser already exists: {vu.email}")
        except VerifiedUser.DoesNotExist:
            print("❌ VerifiedUser missing. Creating it now...")
            
            vu = VerifiedUser.objects.create(
                auth_user_id=emp.auth_user_id,
                full_name=emp.full_name,
                email=emp.email,
                phone_number=emp.phone_number,
                role="employee"
            )
            print(f"✅ Created VerifiedUser: {vu.id}")
            
    except OrganizationEmployee.DoesNotExist:
        print("❌ Employee NOT FOUND.")

if __name__ == "__main__":
    fix_employee_user()
