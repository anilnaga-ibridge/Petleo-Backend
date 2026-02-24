import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, VerifiedUser, ServiceProvider

print("=== Employees Status Check ===")
for emp in OrganizationEmployee.objects.all():
    print(f"Employee: {emp.full_name} ({emp.email})")
    print(f"  Auth ID: {emp.auth_user_id}")
    print(f"  Status: {emp.status}")
    print(f"  Rating: {emp.average_rating} ({emp.total_ratings} reviews)")
    print("-" * 20)

print("\n=== Providers Status Check ===")
for sp in ServiceProvider.objects.all():
    print(f"Provider: {sp.full_name} ({sp.verified_user.email})")
    print(f"  Rating: {sp.average_rating} ({sp.total_ratings} reviews)")
    print("-" * 20)
