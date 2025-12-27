import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider

def create_missing_provider():
    print("--- Creating Missing ServiceProvider Profile ---")
    
    # 1. Get User
    user = VerifiedUser.objects.order_by('-created_at').first()
    print(f"User: {user.email}")
    
    # 2. Check/Create Provider
    provider, created = ServiceProvider.objects.get_or_create(verified_user=user)
    
    if created:
        print(f"✅ Created new ServiceProvider profile for {user.email}")
        # Set some defaults if needed
        provider.business_name = "My Pet Business"
        provider.save()
    else:
        print(f"ℹ️ ServiceProvider profile already exists (ID: {provider.id})")

if __name__ == "__main__":
    create_missing_provider()
