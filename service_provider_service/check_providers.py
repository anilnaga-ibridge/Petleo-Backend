import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider

print(f"{'Name':<25} | {'Profile Status':<15} | {'Verified':<10} | {'Email':<30}")
print("-" * 90)

providers = ServiceProvider.objects.all()
for p in providers:
    name = p.verified_user.full_name or "Unknown"
    email = p.verified_user.email or "No Email"
    print(f"{name:<25} | {p.profile_status:<15} | {str(p.is_fully_verified):<10} | {email:<30}")

print(f"\nTotal Providers: {providers.count()}")
print(f"Active & Verified Count: {providers.filter(profile_status='active', is_fully_verified=True).count()}")
