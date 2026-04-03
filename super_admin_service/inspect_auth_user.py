
import os
import django
import uuid

# Use the HACK from kafka_consumer.py to find the right settings
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service', 'auth_service')))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

auth_user_id = "5ee51be1-7065-43e0-898a-2dca34dd3820"
try:
    user = User.objects.get(id=uuid.UUID(auth_user_id))
    print(f"User Found: {user.full_name}")
    print(f"Email: {user.email}")
    print(f"Avatar URL: {user.avatar_url}")
except User.DoesNotExist:
    print("User not found in Auth Service.")
except Exception as e:
    print(f"Error: {e}")
