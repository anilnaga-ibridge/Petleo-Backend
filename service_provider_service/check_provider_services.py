import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, AllowedService

print(f"{'Name':<25} | {'Services Count':<15}")
print("-" * 45)

providers = ServiceProvider.objects.all()
for p in providers:
    name = p.verified_user.full_name or "Unknown"
    svc_count = AllowedService.objects.filter(verified_user=p.verified_user).count()
    print(f"{name:<25} | {svc_count:<15}")
