import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, AllowedService

def check_allowed_services():
    provider = ServiceProvider.objects.first()
    user = provider.verified_user
    print(f"--- Checking Allowed Services for {user.email} ---")
    services = AllowedService.objects.filter(verified_user=user)
    for s in services:
        print(f"Service ID: {s.service_id}, Name: {s.name}")

if __name__ == "__main__":
    check_allowed_services()
