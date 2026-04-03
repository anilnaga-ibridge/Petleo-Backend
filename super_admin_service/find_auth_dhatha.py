
import os
import django
import sys

# Use the HACK from kafka_consumer.py to find the right settings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Auth_Service', 'auth_service')))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User

try:
    users = User.objects.filter(full_name__icontains="Dhatha")
    for user in users:
        print(f"ID: {user.id} | Name: {user.full_name} | Email: {user.email} | Avatar: {user.avatar_url}")
except Exception as e:
    print(f"Error: {e}")
