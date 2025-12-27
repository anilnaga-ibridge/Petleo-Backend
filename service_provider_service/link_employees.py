import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def link_employees():
    print("--- Linking Employees to Provider ---")
    
    # 1. Get Provider
    user = VerifiedUser.objects.order_by('-created_at').first()
    provider = ServiceProvider.objects.get(verified_user=user)
    print(f"Provider: {provider.id} (User: {user.email})")
    
    # 2. Find Orphaned Employees
    # Since we don't have a direct link if organization_id is null, we might need to rely on 
    # how they were created. 
    # If they were created via the API, they should have been linked.
    # But if the provider didn't exist, maybe they failed?
    # Or maybe they are linked to a DIFFERENT provider?
    
    # Let's check all employees and see who they belong to.
    all_emps = OrganizationEmployee.objects.all()
    
    count = 0
    for emp in all_emps:
        print(f"Checking Employee: {emp.full_name} (Org ID: {emp.organization_id})")
        
        # Force reassign for debugging
        print(f" -> Reassigning from {emp.organization_id} to {provider.id}")
        emp.organization = provider
        emp.save()
        count += 1

    print(f"✅ Linked {count} employees to the provider.")

if __name__ == "__main__":
    link_employees()
