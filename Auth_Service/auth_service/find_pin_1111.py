import os
import django
from django.contrib.auth.hashers import check_password

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

count = 0
for u in User.objects.all():
    if u.pin_hash and check_password("1111", u.pin_hash):
        print(f"User found with PIN 1111: {u.full_name} ({u.phone_number}) ID: {u.id}")
        count += 1

print(f"Finished checking {User.objects.count()} users. Found {count} users with PIN 1111.")
