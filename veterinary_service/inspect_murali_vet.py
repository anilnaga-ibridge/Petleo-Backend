import os
import django
import sys
import json

# Setup Django environment for veterinary_service
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment, Clinic
from veterinary.services import RolePermissionService

def check_murali():
    # Murali's Auth ID from logs
    murali_auth_id = '81804b4a-e4ef-4b47-ba4e-c4a037b514b8'
    
    print(f"--- Diagnosing Murali ({murali_auth_id}) in Veterinary Service ---")
    
    staff = VeterinaryStaff.objects.filter(auth_user_id=murali_auth_id).first()
    if not staff:
        print("❌ VeterinaryStaff profile NOT FOUND.")
        return

    print(f"✅ Staff Found: {getattr(staff, 'full_name', 'No Name')}")
    print(f"   Role: {staff.role}")
    print(f"   Permissions (local): {staff.permissions}")
    
    assignments = StaffClinicAssignment.objects.filter(staff=staff)
    print(f"✅ Assignments Found: {assignments.count()}")
    for a in assignments:
        print(f"   - Clinic: {a.clinic.name} ({a.clinic.id})")
        print(f"     Role: {a.role}")
        print(f"     Permissions: {a.permissions}")
        print(f"     Is Active: {a.is_active}")
        print(f"     Is Primary: {a.is_primary}")
        
        # Resolve permissions
        assigned_role = a.role or staff.role
        print(f"     Resolving perms for role: {assigned_role}")
        resolved = RolePermissionService.get_permissions_for_role(assigned_role)
        print(f"     Resolved Perms Count: {len(resolved)}")
        
        has_visits = any(
            (isinstance(p, str) and p == 'VETERINARY_VISITS') or 
            (isinstance(p, dict) and p.get('capability_key') == 'VETERINARY_VISITS')
            for p in resolved
        )
        print(f"     Has VETERINARY_VISITS: {has_visits}")

if __name__ == "__main__":
    check_murali()
