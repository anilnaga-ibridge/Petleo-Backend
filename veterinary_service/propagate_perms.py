import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment

def propagate():
    print("🚀 Propagating Permissions from Staff to Assignments...")
    
    staff_list = VeterinaryStaff.objects.all()
    count = 0
    for staff in staff_list:
        perms = staff.permissions
        if not perms:
            continue
            
        # Update assignments
        updated = StaffClinicAssignment.objects.filter(staff=staff).update(permissions=perms)
        if updated > 0:
            print(f"✅ Updated {updated} assignments for {staff.auth_user_id} with {len(perms)} perms")
            count += 1
            
    print(f"Done. Updated {count} staff records' assignments.")

if __name__ == "__main__":
    propagate()
