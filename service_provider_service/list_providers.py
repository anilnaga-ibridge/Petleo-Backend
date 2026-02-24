import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider

def list_providers():
    print("--- Listing Providers ---")
    providers = ServiceProvider.objects.all()
    for p in providers:
        print(f"ID: {p.id}, Email: {p.verified_user.email}, Name: {p.verified_user.full_name}")

if __name__ == "__main__":
    list_providers()
