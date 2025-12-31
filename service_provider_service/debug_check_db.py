
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider, VerifiedUser

def check_employees():
    print("Checking OrganizationEmployee records...")
    employees = OrganizationEmployee.objects.all().order_by('-created_at')
    
    print(f"Total Employees Found: {employees.count()}")
    print("-" * 60)
    print(f"{'Full Name':<20} | {'Role':<15} | {'Status':<10} | {'Created At'}")
    print("-" * 60)
    
    for emp in employees:
        print(f"{emp.full_name:<20} | {emp.role:<15} | {emp.status:<10} | {emp.created_at}")

    print("-" * 60)
    
    # Check specifically for receptionist
    receptionists = OrganizationEmployee.objects.filter(role__iexact='receptionist')
    print(f"\nReceptionists found: {receptionists.count()}")
    for r in receptionists:
        print(f"ID: {r.id}, Name: {r.full_name}, AuthID: {r.auth_user_id}")

if __name__ == "__main__":
    check_employees()
