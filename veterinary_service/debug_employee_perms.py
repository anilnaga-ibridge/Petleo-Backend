#!/usr/bin/env python
"""
Debug Employee Permissions Flow
Checks the complete permission sync chain from role assignment to database storage
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment, Clinic

def check_employee_permissions(employee_email=None):
    """Check employee permissions in the veterinary service database"""
    
    print("\n" + "="*100)
    print(" EMPLOYEE PERMISSION DATABASE CHECK")
    print("="*100 + "\n")
    
    # Get all staff if no specific employee
    if employee_email:
        staff_list = VeterinaryStaff.objects.filter(auth_user_id__icontains=employee_email)
    else:
        staff_list = VeterinaryStaff.objects.all().order_by('-created_at')[:10]
    
    print(f"Found {staff_list.count()} staff members\n")
    
    for staff in staff_list:
        print(f"\n{'─'*100}")
        print(f"👤 STAFF: {staff.auth_user_id}")
        print(f"{'─'*100}")
        print(f"   ID: {staff.id}")
        print(f"   Role: {staff.role}")
        print(f"   Legacy Clinic: {staff.clinic}")
        print(f"   Base Permissions: {staff.permissions}")
        print(f"   Permission Count: {len(staff.permissions) if staff.permissions else 0}")
        
        # Check assignments
        assignments = StaffClinicAssignment.objects.filter(staff=staff)
        print(f"\n   📋 CLINIC ASSIGNMENTS ({assignments.count()}):")
        
        if assignments.exists():
            for assignment in assignments:
                try:
                    clinic = Clinic.objects.get(id=assignment.clinic_id)
                    print(f"\n      🏥 {clinic.name} (ID: {clinic.id})")
                    print(f"         Org ID: {clinic.organization_id}")
                    print(f"         Role: {assignment.role}")
                    print(f"         Permissions: {assignment.permissions}")
                    print(f"         Permission Count: {len(assignment.permissions) if assignment.permissions else 0}")
                    print(f"         Is Primary: {assignment.is_primary}")
                    print(f"         Is Active: {assignment.is_active}")
                    
                    if not assignment.is_active:
                        print(f"         ⚠️  WARNING: Assignment is INACTIVE!")
                    
                    if not assignment.permissions or len(assignment.permissions) == 0:
                        print(f"         ❌ ERROR: No permissions assigned!")
                        
                except Clinic.DoesNotExist:
                    print(f"      ❌ ERROR: Clinic {assignment.clinic_id} not found!")
        else:
            print("      ⚠️  NO ASSIGNMENTS FOUND")
            print("      This employee cannot access any clinic!")
    
    print(f"\n{'='*100}\n")
    
    # Summary check
    print("🔍 COMMON ISSUES TO CHECK:")
    print("   1. ❓ Is the employee's auth_user_id correct in VeterinaryStaff?")
    print("   2. ❓ Does the employee have a StaffClinicAssignment?")
    print("   3. ❓ Is the assignment.is_active = True?")
    print("   4. ❓ Does assignment.permissions contain the expected capabilities?")
    print("   5. ❓ Does the clinic exist and have the correct organization_id?")
    print(f"\n{'='*100}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Check employee permissions in database')
    parser.add_argument('--email', help='Employee email or auth_user_id to filter', required=False)
    args = parser.parse_args()
    
    check_employee_permissions(args.email)
