
import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription

def check_user_data(phone_number):
    try:
        user = VerifiedUser.objects.get(phone_number=phone_number)
        print(f"User found: {user.email} (ID: {user.auth_user_id})")
        
        # Check Subscriptions
        subs = ProviderSubscription.objects.filter(verified_user=user)
        print(f"\nSubscriptions ({subs.count()}):")
        now = timezone.now()
        print(f"Current Time: {now}")
        
        for s in subs:
            print(f"Plan: {s.plan_id}")
            print(f"  Start: {s.start_date}")
            print(f"  End:   {s.end_date}")
            print(f"  Active: {s.is_active}")
            
            is_valid = s.is_active and (not s.end_date or s.end_date >= now)
            print(f"  -> Valid: {is_valid}")

    except VerifiedUser.DoesNotExist:
        print(f"User with phone number {phone_number} not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_user_data('8522047175')
