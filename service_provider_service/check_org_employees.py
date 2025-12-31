
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider

def list_org_employees():
    # ID from logs: 5d560f6b-a1cb-4025-b7bb-87ef212f8a1c
    # This is likely the VerifiedUser ID of the Organization.
    # We need to find the ServiceProvider associated with it.
    
    org_user_id = "7470623a-ee4b-4922-99f5-3ce2f17171d7"
    
    print(f"🔍 Looking for Organization with User ID: {org_user_id}")
    
    try:
        provider = ServiceProvider.objects.get(verified_user__auth_user_id=org_user_id)
        print(f"✅ Found Provider: {provider.id} (Status: {provider.profile_status})")
        
        employees = OrganizationEmployee.objects.filter(organization=provider).order_by('-created_at')
        
        print(f"\n📋 Total Employees: {employees.count()}")
        print("=" * 80)
        print(f"{'Full Name':<25} | {'Role':<15} | {'Status':<10} | {'Email'}")
        print("=" * 80)
        
        for emp in employees:
            print(f"{emp.full_name:<25} | {emp.role:<15} | {emp.status:<10} | {emp.email}")
            
        print("=" * 80)
        
        # Count by role
        from django.db.models import Count
        role_counts = employees.values('role').annotate(count=Count('role'))
        print("\n📊 Role Breakdown:")
        for rc in role_counts:
            print(f"   - {rc['role']}: {rc['count']}")

    except ServiceProvider.DoesNotExist:
        print("❌ Organization not found.")

if __name__ == "__main__":
    list_org_employees()
