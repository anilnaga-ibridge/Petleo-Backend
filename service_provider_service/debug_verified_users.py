import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

def list_users():
    users = VerifiedUser.objects.all()
    print(f"Total VerifiedUsers: {users.count()}")
    print("-" * 80)
    print(f"{'ID (PK)':<38} | {'Auth User ID':<38} | {'Email'}")
    print("-" * 80)
    for user in users:
        print(f"{str(user.id):<38} | {str(user.auth_user_id):<38} | {user.email}")

if __name__ == "__main__":
    list_users()
