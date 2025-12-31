
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription

def rollback_subscriptions(phone_number):
    try:
        user = VerifiedUser.objects.get(phone_number=phone_number)
        print(f"User found: {user.email} (ID: {user.auth_user_id})")
        
        # Delete all subscriptions for this user
        subs = ProviderSubscription.objects.filter(verified_user=user)
        count = subs.count()
        
        if count > 0:
            print(f"Found {count} subscriptions. Deleting...")
            subs.delete()
            print("Successfully deleted subscriptions.")
        else:
            print("No subscriptions found to delete.")

    except VerifiedUser.DoesNotExist:
        print(f"User with phone number {phone_number} not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    rollback_subscriptions('8522047175')
