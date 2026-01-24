
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()
from users.models import User
user_id = "076875b0-ca6b-4d96-a5a5-36f29e8cd976"
try:
    user = User.objects.get(id=user_id)
    print(f"FOUND in Auth_Service: {user.email} | {user.role} | {user.full_name}")
except User.DoesNotExist:
    print(f"NOT FOUND in Auth_Service: User {user_id}")
