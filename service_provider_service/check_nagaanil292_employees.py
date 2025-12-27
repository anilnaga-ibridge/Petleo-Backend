import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def check_nagaanil292_employees():
    print("--- Checking Employees for nagaanil292 ---")
    
    try:
        user = VerifiedUser.objects.get(email='nagaanil292@gmail.com')
        provider = ServiceProvider.objects.get(verified_user=user)
        print(f"Provider: {user.email} (ID: {provider.id})")
        
        emps = OrganizationEmployee.objects.filter(organization=provider)
        print(f"Employees Found: {emps.count()}")
        for emp in emps:
            print(f" - {emp.full_name}")
            
    except VerifiedUser.DoesNotExist:
        print("User nagaanil292 not found.")
    except ServiceProvider.DoesNotExist:
        print("Provider profile still missing!")

if __name__ == "__main__":
    check_nagaanil292_employees()
