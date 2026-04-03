import os
import django
import sys

# Setup Django environment for veterinary_service
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment, Clinic

def check_staff():
    staff_ids = {
        'Murali': '81804b4a-e4ef-4b47-ba4e-c4a037b514b8',
        'Matlu': '166c8f2d-74e1-43ef-8ff4-c5ea435555cb',
        'Manohar': '3d34dd09-e1ae-4148-8df4-051833d7b7e5'
    }
    
    print("--- Staff Sync Status (Veterinary Service) ---")
    for name, auth_id in staff_ids.items():
        staff = VeterinaryStaff.objects.filter(auth_user_id=auth_id).first()
        if staff:
            print(f"✅ {name} ({auth_id}): FOUND. Role: {staff.role}")
        else:
            print(f"❌ {name} ({auth_id}): NOT FOUND.")

if __name__ == "__main__":
    check_staff()
