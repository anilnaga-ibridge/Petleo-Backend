import os
import django
from django.contrib.auth.hashers import check_password

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

phone = "6345654678"
try:
    user = User.objects.get(phone_number=phone)
    print(f"User: {user.full_name} ({user.email})")
    print(f"PIN Hash: {user.pin_hash}")
    print(f"PIN Set At: {user.pin_set_at}")
    print(f"PIN Expires At: {user.pin_expires_at}")
    
    # Test some common pins
    pins_to_test = ["1234", "1111", "0000", "5555", "123456"]
    for p in pins_to_test:
        if user.pin_hash and check_password(p, user.pin_hash):
            print(f"✅ PIN '{p}' MATCHES!")
        else:
            pass
            # print(f"❌ PIN '{p}' does not match.")

except User.DoesNotExist:
    print(f"User with phone {phone} not found.")
