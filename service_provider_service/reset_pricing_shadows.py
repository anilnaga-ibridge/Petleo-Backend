import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderPricing

def reset_shadows():
    email = "nagaanil29@gmail.com"
    try:
        user = VerifiedUser.objects.get(email=email)
    except VerifiedUser.DoesNotExist:
        print(f"User {email} not found")
        return

    service_id = "2170653c-9de5-4f61-b1ca-35b1a0439b17"
    
    # Delete all custom pricing for this service (Active and Inactive)
    count, _ = ProviderPricing.objects.filter(
        provider=user, 
        service_id=service_id
    ).delete()
    
    print(f"Deleted {count} custom/shadow pricing records for service {service_id}")

if __name__ == "__main__":
    reset_shadows()
