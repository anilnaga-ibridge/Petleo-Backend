import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

def inspect_recent_users():
    print("--- Inspecting Recent Users (Last 5) ---")
    
    users = VerifiedUser.objects.order_by('-created_at')[:5]
    
    for user in users:
        print(f"\nUser: {user.email} (Role: {user.role})")
        print(f"  Auth ID: {user.auth_user_id}")
        print(f"  Created At: {user.created_at}")
        
        try:
            provider = ServiceProvider.objects.get(verified_user=user)
            print(f"  ✅ ServiceProvider Profile: {provider.id}")
            
            # Check employees for this provider
            emps = OrganizationEmployee.objects.filter(organization=provider)
            print(f"  👥 Employees: {emps.count()}")
            for emp in emps:
                print(f"    - {emp.full_name} ({emp.email}) [Status: {emp.status}]")
                
        except ServiceProvider.DoesNotExist:
            print(f"  ❌ NO ServiceProvider Profile!")
            
            # Check if there are any employees linked to this Auth ID (orphaned?)
            # OrganizationEmployee doesn't link to the *creator* directly, only via 'organization'.
            # But we can check 'created_by' if we had that field? 
            # The model has 'created_by' field? Let's check.
            pass

if __name__ == "__main__":
    inspect_recent_users()
