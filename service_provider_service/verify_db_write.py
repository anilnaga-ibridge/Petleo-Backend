import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService

def verify():
    auth_id = "4ce26186-7b1c-4b82-949c-e69e9431be68"
    
    from django.db import connection
    print(f"DB Name: {connection.settings_dict['NAME']}")
    print(f"DB Port: {connection.settings_dict['PORT']}")
    print(f"VerifiedUsers Count: {VerifiedUser.objects.count()}")
    
    user = VerifiedUser.objects.get(auth_user_id=auth_id)
    print(f"User ID: {user.id}")
    
    # Check count
    count = ProviderCapabilityAccess.objects.filter(user=user).count()
    print(f"Current Count: {count}")
    
    # Try creating one
    # Need a service 
    svc = ProviderTemplateService.objects.first()
    if not svc:
        print("No services found!")
        return

    print(f"Creating test access for service {svc.name}")
    try:
        pca = ProviderCapabilityAccess.objects.create(
            user=user,
            service_id=svc.super_admin_service_id,
            can_view=True
        )
        print(f"Created PCA: {pca.id}")
        
        count_after = ProviderCapabilityAccess.objects.filter(user=user).count()
        print(f"Count after create: {count_after}")
        
    except Exception as e:
        print(f"Error creating: {e}")

if __name__ == "__main__":
    verify()
