
import os
import sys
import django
from django.conf import settings

# Setup Django for Veterinary Service
if not settings.configured:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
    django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment, Clinic

def check_db():
    print("🚀 Checking Veterinary Service DB for Vitals Access...")
    
    # 1. List all Staff with Vitals capability
    print("\n[1] Checking VeterinaryStaff Table:")
    staff_with_vitals = []
    all_staff = VeterinaryStaff.objects.all()
    for s in all_staff:
        perms = s.permissions or []
        if 'VETERINARY_VITALS' in perms:
            staff_with_vitals.append(s)
        else:
            print(f"   - Staff {s.auth_user_id} ({s.role}): MISSING VITALS. Perms: {perms}")
            
    print(f"   -> Found {len(staff_with_vitals)} staff with VETERINARY_VITALS.")

    # 2. Check Assignments
    print("\n[2] Checking StaffClinicAssignment Table:")
    assignments = StaffClinicAssignment.objects.all()
    for a in assignments:
        perms = a.permissions or []
        has_vitals = 'VETERINARY_VITALS' in perms
        status = "✅ OK" if has_vitals else "❌ MISSING"
        print(f"   - Assign {a.staff.auth_user_id} @ {a.clinic.name}: {status}")

if __name__ == "__main__":
    check_db()
