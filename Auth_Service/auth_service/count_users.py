import os
import sys
import django

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import User

def count_users():
    count = User.objects.count()
    print(f"Total Users: {count}")

if __name__ == "__main__":
    count_users()
