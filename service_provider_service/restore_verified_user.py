import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

def restore_user():
    auth_user_id = "83d93dbf-1afc-41e1-bc8f-ff95d6e0bf11"
    email = "prem@gmail.com"
    
    print(f"Restoring user {email} with ID {auth_user_id}...")
    
    # Create user with id=auth_user_id
    user, created = VerifiedUser.objects.update_or_create(
        id=auth_user_id,
        defaults={
            "auth_user_id": auth_user_id,
            "email": email,
            "full_name": "Prem", # Placeholder
            "role": "individual", # Placeholder
            "permissions": []
        }
    )
    
    print(f"User restored: {user.id} (Auth ID: {user.auth_user_id})")
    print(f"Created: {created}")

if __name__ == "__main__":
    restore_user()
