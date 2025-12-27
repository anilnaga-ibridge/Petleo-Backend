import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser

def check_json_perms():
    print("--- Checking VerifiedUser JSON Permissions ---")
    
    user = VerifiedUser.objects.filter(email='nagaanil29@gmail.com').first()
    if not user:
        print("User not found")
        return

    print(f"User: {user.email}")
    print(f"JSON Permissions: {user.permissions}")
    
    if user.permissions:
        print("⚠️ Found data in JSON permissions field!")
        # Clear it just in case
        user.permissions = []
        user.save()
        print("✅ Cleared JSON permissions.")
    else:
        print("✅ JSON permissions are empty.")

if __name__ == "__main__":
    check_json_perms()
