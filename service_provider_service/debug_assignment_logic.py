import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def debug_assignment():
    email = "nagaanil29@gmail.com"
    emp_id = "8ef65056-e082-4e56-bc57-4bf05f93aea0"
    
    print(f"--- Debugging Assignment for {email} -> Emp {emp_id} ---")
    
    # 1. Get User
    try:
        user = VerifiedUser.objects.get(email=email)
        print(f"✅ User Found: {user.id} (Auth: {user.auth_user_id})")
    except VerifiedUser.DoesNotExist:
        print("❌ User not found")
        return

    # 2. Get Provider
    try:
        provider = ServiceProvider.objects.get(verified_user=user)
        print(f"✅ Provider Found: {provider.id}")
    except ServiceProvider.DoesNotExist:
        print("❌ Provider not found for user")
        return

    # 3. Get Employee
    try:
        emp = OrganizationEmployee.objects.get(id=emp_id, organization=provider)
        print(f"✅ Employee Found: {emp.id}")
        print(f"   Linked to Org: {emp.organization.id}")
    except OrganizationEmployee.DoesNotExist:
        print("❌ Employee NOT FOUND for this provider.")
        
        # Debug why
        try:
            actual_emp = OrganizationEmployee.objects.get(id=emp_id)
            print(f"   ⚠️ Employee exists but belongs to Org: {actual_emp.organization.id}")
            print(f"   ⚠️ Expected Org: {provider.id}")
            
            if actual_emp.organization.id != provider.id:
                print("   ❌ MISMATCH! The employee belongs to a different ServiceProvider instance.")
                print(f"   Provider User: {provider.verified_user.email}")
                print(f"   Actual Org User: {actual_emp.organization.verified_user.email}")
                
        except OrganizationEmployee.DoesNotExist:
            print("   ❌ Employee does not exist at all.")

if __name__ == "__main__":
    debug_assignment()
