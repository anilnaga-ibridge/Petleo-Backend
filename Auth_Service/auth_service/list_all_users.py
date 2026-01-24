import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import User

print("Checking User table in Auth_Service...")
users = User.objects.all()
for user in users:
    print(f"User: {user.email}, ID: {user.id}, Role: {user.role}")

print("Done.")
