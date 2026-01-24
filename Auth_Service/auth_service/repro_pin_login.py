
import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.views import is_pin_valid_today
from users.models import User

# Check specific user
email = "eswar@gmail.com"
try:
    user = User.objects.get(email=email)
    print(f"Testing is_pin_valid_today for {email}")
    is_valid = is_pin_valid_today(user)
    print(f"Result: {is_valid}")
    
    if not is_valid:
        print("PASS: PIN is considered expired as expected.")
    else:
        print("FAIL: PIN is considered VALID despite being old.")
        
except User.DoesNotExist:
    print(f"User {email} not found.")

