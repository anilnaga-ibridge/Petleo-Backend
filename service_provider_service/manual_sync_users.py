
import os
import django
import sys
import uuid

# Setup Django environment for Service Provider Service
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser

# Missing users identified from manual comparison
# Format: (email, auth_user_id, role, full_name, phone_number)
missing_users = [
    ("superadmin@example.com", "55bdf699-d21f-4cc3-a7b4-65bc37c3394b", "superadmin", "Super Admin", "9876543210"),
    ("mahesh@gmail.com", "e0515a9b-665b-495b-9ff2-af995f04bf19", "receptionist", "Mahesh", "1234567890"),
    ("clinic@test.com", "6d2d8c21-d908-48eb-9791-4b149dc4a9a0", "organization", "Clinic Org", "1122334455"),
    ("das@gmail.com", "66874c90-2059-4b18-a17b-34963fc0c9af", "organization", "Das Org", "2233445566"),
    ("eswar@gmail.com", "ba71d76b-9a71-4c10-9eb3-6fa0a2147ec9", "employee", "Eswar", "3344556677"),
    ("doctor@gmail.com", "5b3578d9-f5c1-4f9c-bc43-0d25caa47ca8", "doctor", "Dr. Doctor", "4455667788"),
     ("receptionist2@gmail.com", "0160b0e8-dbc2-4d99-afaa-59bdfdfa4356", "lab tech", "Receptionist Two", "5566778899")
]

print("Syncing missing users to provider_db...")

count = 0
for email, auth_id, role, name, phone in missing_users:
    if not VerifiedUser.objects.filter(auth_user_id=auth_id).exists():
        print(f"Creating missing user: {email} ({auth_id})")
        VerifiedUser.objects.create(
            auth_user_id=auth_id,
            email=email,
            full_name=name,
            phone_number=phone,
            role=role,
            permissions=[] # Default to empty list
        )
        count += 1
    else:
        print(f"User {email} already exists.")

print(f"\nSynced {count} users.")
