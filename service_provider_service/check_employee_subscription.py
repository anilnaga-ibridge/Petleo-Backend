import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee, ProviderSubscription

def check_subscription():
    emp_id = "8ef65056-e082-4e56-bc57-4bf05f93aea0"
    print(f"--- Checking Subscription for Employee {emp_id} ---")
    
    try:
        emp = OrganizationEmployee.objects.get(id=emp_id)
        user = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
        print(f"✅ User: {user.email}")
        
        sub = ProviderSubscription.objects.filter(verified_user=user).first()
        if sub:
            print(f"✅ Subscription Found: {sub.plan_id} (Active: {sub.is_active})")
        else:
            print("❌ NO Subscription found for this employee.")
            
            # Check Org's subscription
            org_sub = ProviderSubscription.objects.filter(verified_user=emp.organization.verified_user).first()
            if org_sub:
                print(f"ℹ️ Organization ({emp.organization.verified_user.email}) has subscription: {org_sub.plan_id}")
            else:
                print("❌ Organization also has NO subscription!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_subscription()
