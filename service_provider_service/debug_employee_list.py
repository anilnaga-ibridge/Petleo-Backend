import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def debug_employee_list():
    print("--- Debugging Employee List ---")
    
    # 1. Get Latest User (Assuming this is the Organization Provider)
    user = VerifiedUser.objects.order_by('-created_at').first()
    print(f"User: {user.email} (Auth ID: {user.auth_user_id})")
    
    # 2. Find ServiceProvider Profile
    try:
        provider = ServiceProvider.objects.get(verified_user=user)
        print(f"✅ Found ServiceProvider Profile (ID: {provider.id})")
    except ServiceProvider.DoesNotExist:
        print("❌ ServiceProvider Profile NOT FOUND for this user.")
        return

    # 3. Fetch Employees
    employees = OrganizationEmployee.objects.filter(organization=provider, deleted_at__isnull=True)
    print(f"Found {employees.count()} active employees.")
    
    for emp in employees:
        print(f" - {emp.full_name} ({emp.email}) - Status: {emp.status}")

    # 4. Check for ANY employees linked to this user's Auth ID (in case of mismatch)
    print("\n--- Checking for Mismatches ---")
    all_emps = OrganizationEmployee.objects.all()
    print(f"Total Employees in DB: {all_emps.count()}")
    
    # Check if any employees have organization_id matching our provider
    linked_emps = OrganizationEmployee.objects.filter(organization_id=provider.id)
    print(f"Employees linked to Provider ID {provider.id}: {linked_emps.count()}")

if __name__ == "__main__":
    debug_employee_list()
