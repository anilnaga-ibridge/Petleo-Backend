
import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import User

# Check specific user (e.g., mahesh@gmail.com based on previous context, or list all with PINs)
print("Checking PIN expiration for users...")
users = User.objects.filter(pin_hash__isnull=False)

for user in users:
    print(f"User: {user.email}")
    print(f"  PIN Set At:     {user.pin_set_at}")
    print(f"  PIN Expires At: {user.pin_expires_at}")
    print(f"  Current Time:   {timezone.now()}")
    if user.pin_expires_at:
        remaining = user.pin_expires_at - timezone.now()
        print(f"  Remaining:      {remaining}")
        expired = timezone.now() >= user.pin_expires_at
        print(f"  Expired:        {expired}")
    else:
        print("  No Expiration Set")
    print("-" * 30)
