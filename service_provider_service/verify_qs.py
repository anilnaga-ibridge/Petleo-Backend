import os
import django
import sys
from types import SimpleNamespace

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ServiceProvider
from service_provider.models_scheduling import EmployeeDailySchedule

# Gopi's Auth ID
GOPI_AUTH_ID = '87b9cb5d-ee9e-4e20-bf22-646b30b793ed'

class MockRequest:
    def __init__(self, auth_user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # Find or create a user object with this auth_user_id
        # In this system, user objects usually have auth_user_id
        # But we can just mock a user object
        self.user = SimpleNamespace(auth_user_id=auth_user_id)
        # Add provider_profile if they are an owner
        try:
            p = ServiceProvider.objects.get(verified_user__auth_user_id=auth_user_id)
            self.user.provider_profile = p
        except ServiceProvider.DoesNotExist:
            pass

def simulate_get_queryset(auth_user_id):
    request = MockRequest(auth_user_id)
    user = request.user
    queryset = EmployeeDailySchedule.objects.all()
    
    print(f"--- Simulating get_queryset for User: {auth_user_id} ---")
    if hasattr(user, 'provider_profile'):
        print(f"User is a PROVIDER for Org: {user.provider_profile.id}")
        return queryset.filter(employee__organization=user.provider_profile)
        
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        print(f"User is an EMPLOYEE: {emp.full_name}")
        return queryset.filter(employee=emp)
    except OrganizationEmployee.DoesNotExist:
        print("User is neither.")
        pass
        
    return queryset.none()

# Test for Gopi
results = simulate_get_queryset(GOPI_AUTH_ID)
print(f"Results count for Gopi: {results.count()}")
for s in results:
    print(f" - {s.employee.full_name} | {s.date} | {s.start_time}-{s.end_time}")

# Test for Rahul (who is NOT an owner)
results_rahul = simulate_get_queryset('5c3b54b9-aa99-441d-8598-df3aea0b59fd')
print(f"\nResults count for Rahul: {results_rahul.count()}")
for s in results_rahul:
    print(f" - {s.employee.full_name} | {s.date} | {s.start_time}-{s.end_time}")
