import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, StaffClinicAssignment

def fix_vet_roles():
    # 1. Fix Praveen's specific role mismatch
    # Praveen's Auth ID identified earlier: 66e9b147-e9bc-432c-b78b-b513a9b22901
    praveen_auth_id = '66e9b147-e9bc-432c-b78b-b513a9b22901'
    
    # Update VeterinaryStaff record
    staff = VeterinaryStaff.objects.filter(auth_user_id=praveen_auth_id).first()
    if staff:
        print(f"Updating Praveen (Staff): {staff.role} -> employee")
        staff.role = 'employee'
        staff.save()
        
        # Update Assignment (Crucial for UI)
        assignments = StaffClinicAssignment.objects.filter(staff=staff)
        for ass in assignments:
            print(f"Updating Praveen Assignment: {ass.role} -> Receptionist")
            ass.role = 'Receptionist'
            ass.save()
    
    # 2. Standardize 'type' to 'employee' for others in the same clinic
    # Logic: If it's not 'employee', but they are staff, they should be type 'employee'
    all_staff = VeterinaryStaff.objects.all()
    count = 0
    for s in all_staff:
        if s.role and s.role != 'employee':
             print(f"Standardizing Staff {s.auth_user_id}: {s.role} -> employee")
             s.role = 'employee'
             s.save()
             count += 1
             
    # Assignments are often used for display in the employee list
    all_ass = StaffClinicAssignment.objects.all()
    # Exceptions: We want to KEEP 'Receptionist', 'doctor', 'Nurse' if that's what the user wants,
    # BUT the user said "type is always employee". 
    # Usually the UI shows: [Role Name] [Type]
    # In the user's screenshot: "Trainer employee" 
    # Here Trainer is the role, employee is the type.
    # If the database has Role: Nurse, Type: employee -> Nurse employee.
    
    # Let's ensure Jhony (doctor) and others follow this.
    # Jhony: doctor -> employee
    # Nurse: Nurse -> employee
    
    for ass in all_ass:
        if ass.staff.auth_user_id == praveen_auth_id:
            continue # Already handled explicitly
            
        if ass.role in ['doctor', 'Nurse']:
            print(f"Standardizing Assignment {ass.id}: {ass.role} -> employee")
            ass.role = 'employee'
            ass.save()
            count += 1

    print(f"✅ Synchronized and standardized {count} records in veterinary_service.")

if __name__ == "__main__":
    fix_vet_roles()
