import os
import django
import sys

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta, datetime

User = get_user_model()

def reset_pin():
    try:
        user = User.objects.get(email='superadmin@example.com')
        print(f"Found user: {user.email}")
        
        # Reset PIN to '1234'
        new_pin = '1234'
        user.pin_hash = make_password(new_pin)
        
        # Set expiry to tomorrow midnight
        tz = timezone.get_current_timezone()
        now = timezone.now().astimezone(tz)
        tomorrow = now.date() + timedelta(days=1)
        midnight = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
        
        user.pin_set_at = now
        user.pin_expires_at = midnight
        
        user.save()
        print(f"✅ Successfully reset PIN to '{new_pin}' for {user.email}")
        
    except User.DoesNotExist:
        print("❌ User superadmin@example.com not found!")
    except Exception as e:
        print(f"❌ Error resetting PIN: {str(e)}")

if __name__ == "__main__":
    reset_pin()
