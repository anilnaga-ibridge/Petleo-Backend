import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, ProviderSubscription

print(f"{'Name':<25} | {'Profile Status':<15} | {'Verified':<10} | {'Sub Active':<10}")
print("-" * 75)

providers = ServiceProvider.objects.all()
for p in providers:
    name = p.verified_user.full_name or "Unknown"
    sub_active = ProviderSubscription.objects.filter(verified_user=p.verified_user, is_active=True).exists()
    print(f"{name:<25} | {p.profile_status:<15} | {str(p.is_fully_verified):<10} | {str(sub_active):<10}")

print(f"\nTotal Providers: {providers.count()}")
print(f"Active & Verified & Subscriped Count: {ServiceProvider.objects.filter(profile_status='active', is_fully_verified=True, verified_user__subscription__is_active=True).distinct().count()}")
