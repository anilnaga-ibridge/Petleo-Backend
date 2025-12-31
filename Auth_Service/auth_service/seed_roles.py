
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import Role

def seed_roles():
    roles_to_ensure = [
        'receptionist', 
        'vitals staff', 
        'doctor', 
        'lab tech', 
        'pharmacy', 
        'veterinarian', 
        'groomer'
    ]
    
    print("🌱 Seeding Roles...")
    for role_name in roles_to_ensure:
        role, created = Role.objects.get_or_create(name=role_name)
        if created:
            print(f"✅ Created role: {role_name}")
        else:
            print(f"ℹ️ Role exists: {role_name}")

if __name__ == "__main__":
    seed_roles()
