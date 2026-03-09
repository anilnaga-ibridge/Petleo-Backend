import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import Clinic, StaffClinicAssignment, VeterinaryStaff

def diagnose():
    print("--- Clinic Search ---")
    # Gopi's OrgID: 87b9cb5d-ee9e-4e20-bf22-646b30b793ed
    clinics = Clinic.objects.filter(organization_id='87b9cb5d-ee9e-4e20-bf22-646b30b793ed')
    c_data = []
    for c in clinics:
        c_data.append({
            "name": c.name,
            "id": str(c.id),
            "organization_id": c.organization_id,
            "is_primary": c.is_primary
        })
    print(json.dumps(c_data, indent=2))

    print("\n--- Staff Clinic Assignment Search (by Staff Auth ID) ---")
    # Gopi's Auth User ID: 87b9cb5d-ee9e-4e20-bf22-646b30b793ed
    assignments = StaffClinicAssignment.objects.filter(staff__auth_user_id='87b9cb5d-ee9e-4e20-bf22-646b30b793ed')
    a_data = []
    for a in assignments:
        a_data.append({
            "staff_auth_id": a.staff.auth_user_id,
            "clinic_name": a.clinic.name,
            "clinic_id": str(a.clinic.id),
            "role": a.role,
            "is_active": a.is_active,
            "specialization": a.specialization,
            "consultation_fee": str(a.consultation_fee)
        })
    print(json.dumps(a_data, indent=2))

    print("\n--- Searching for 'Gopi' in VeterinaryStaff ---")
    staf = VeterinaryStaff.objects.filter(auth_user_id='87b9cb5d-ee9e-4e20-bf22-646b30b793ed')
    s_data = []
    for s in staf:
        s_data.append({
            "auth_user_id": s.auth_user_id,
        })
    print(json.dumps(s_data, indent=2))

if __name__ == "__main__":
    diagnose()
