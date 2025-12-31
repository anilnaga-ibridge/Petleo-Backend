
import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/Auth_Service/auth_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_service.settings')
django.setup()

from users.models import Role

def list_roles():
    print("🔍 Checking Auth Service Roles...")
    roles = Role.objects.all()
    print(f"Total Roles: {roles.count()}")
    print("-" * 40)
    for r in roles:
        print(f"ID: {r.id} | Name: {r.name}")
    print("-" * 40)

    required_roles = ['receptionist', 'veterinarian', 'groomer', 'doctor', 'labtech', 'pharmacy', 'vitalsstaff']
    missing = []
    for req in required_roles:
        if not roles.filter(name__iexact=req).exists():
            missing.append(req)
    
    if missing:
        print(f"❌ Missing Roles: {', '.join(missing)}")
    else:
        print("✅ All required roles exist.")

if __name__ == "__main__":
    list_roles()
