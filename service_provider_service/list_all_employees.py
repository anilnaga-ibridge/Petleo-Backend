import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee, ProviderSubscription

def list_all():
    org_email = "nagaanil29@gmail.com"
    print(f"--- Employees for Org {org_email} ---")
    
    try:
        org_user = VerifiedUser.objects.get(email=org_email)
        employees = OrganizationEmployee.objects.filter(organization__verified_user=org_user)
        
        for emp in employees:
            print(f"\nEmployee: {emp.full_name} ({emp.email})")
            print(f"  Auth ID: {emp.auth_user_id}")
            
            try:
                vu = VerifiedUser.objects.get(auth_user_id=emp.auth_user_id)
                print(f"  VerifiedUser: {vu.email}")
                
                sub = ProviderSubscription.objects.filter(verified_user=vu).first()
                if sub:
                    print(f"  ✅ Subscription: {sub.plan_id}")
                else:
                    print("  ❌ NO Subscription")
                    
                perms = vu.capabilities.all()
                print(f"  Permissions Count: {perms.count()}")
                
            except VerifiedUser.DoesNotExist:
                print("  ❌ VerifiedUser MISSING")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_all()
