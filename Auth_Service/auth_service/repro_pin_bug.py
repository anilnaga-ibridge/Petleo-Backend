import os
import django
from django.contrib.auth.hashers import check_password, make_password

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

phone = "6345654678"
try:
    user = User.objects.get(phone_number=phone)
    print(f"User: {user.full_name}")
    print(f"Actual PIN Hash: {user.pin_hash}")
    
    # Test '1111'
    if check_password("1111", user.pin_hash):
        print("✅ '1111' MATCHES.")
    else:
        print("❌ '1111' DOES NOT MATCH.")
        
    # Test '0000' (random)
    if check_password("0000", user.pin_hash):
        print("🚨 BUG: '0000' ALSO MATCHES!")
    else:
        print("✅ '0000' does not match.")

except User.DoesNotExist:
    print(f"User with phone {phone} not found.")
