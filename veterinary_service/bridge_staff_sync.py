import os
import django
import sys
import uuid

# 1. SETUP VETERINARY SERVICE (Port 8004)
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment, Clinic

# 2. CONFIG
CLINIC_ID = 'e56f30a2-cd65-45c3-8029-2152ed13904a' # Public Clinic
STAFF_DATA = [
    {
        'name': 'Murali',
        'auth_id': '81804b4a-e4ef-4b47-ba4e-c4a037b514b8',
        'role': 'Receptionist'
    },
    {
        'name': 'Matlu',
        'auth_id': '166c8f2d-74e1-43ef-8ff4-c5ea435555cb',
        'role': 'Practice Manager'
    },
    {
        'name': 'Manohar',
        'auth_id': '3d34dd09-e1ae-4148-8df4-051833d7b7e5',
        'role': 'Receptionist'
    }
]

def bridge_staff():
    print(f"--- Bridging Staff to Clinic {CLINIC_ID} ---")
    
    clinic = Clinic.objects.filter(id=CLINIC_ID).first()
    if not clinic:
        print(f"❌ Clinic {CLINIC_ID} NOT FOUND in Veterinary Service.")
        return

    for data in STAFF_DATA:
        auth_id = data['auth_id']
        name = data['name']
        role = data['role']
        
        print(f"Processing {name}...")
        
        # 1. Create/Update VeterinaryStaff (Clinical Profile)
        # Note: Model fields are auth_user_id, full_name, role, permissions
        staff, created = VeterinaryStaff.objects.update_or_create(
            auth_user_id=auth_id,
            defaults={
                'role': role,
                'full_name': name,
                'permissions': [] 
            }
        )
        print(f"   - { '✅ Created' if created else '✅ Updated' } VeterinaryStaff profile.")

        # 2. Create/Update StaffClinicAssignment
        # Note: Model fields are staff, clinic, role, permissions, is_active, is_primary, is_online_available, specialization, consultation_fee
        assignment, a_created = StaffClinicAssignment.objects.update_or_create(
            staff=staff,
            clinic=clinic,
            defaults={
                'role': role,
                'is_active': True,
                'is_primary': True,
                'permissions': [] # Let it fallback to RolePermissionService defaults
            }
        )
        print(f"   - { '✅ Created' if a_created else '✅ Updated' } Clinic Assignment.")

    print("\n--- SYNC COMPLETE ---")
    print("Murali, Matlu, and Manohar are now registered for Clinical Operations.")

if __name__ == "__main__":
    bridge_staff()
