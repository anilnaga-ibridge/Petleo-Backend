"""
Fix Script: Create StaffClinicAssignment for Gopi g in veterinary_service.

Gopi g has a VeterinaryStaff record but NO StaffClinicAssignment in his clinic.
This means VeterinaryAvailabilityService.get_doctor_available_slots() returns []
because it filters on StaffClinicAssignment with role='DOCTOR'.

Run this script from the veterinary_service directory:
    python3 fix_gopi_vet_assignment.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import Clinic, VeterinaryStaff, StaffClinicAssignment

# Gopi g's known identifiers
GOPI_AUTH_USER_ID = '87b9cb5d-ee9e-4e20-bf22-646b30b793ed'
GOPI_CLINIC_ID = '8661f33e-26b0-484c-af2b-7a3cf4334c48'  # Clinic "Gopi" in vet_service

def fix_gopi_vet_assignment():
    print("🔍 Looking up Gopi's Clinic...")
    try:
        clinic = Clinic.objects.get(id=GOPI_CLINIC_ID)
        print(f"✅ Clinic found: {clinic.name} (org={clinic.organization_id})")
    except Clinic.DoesNotExist:
        print("❌ Clinic not found. Aborting.")
        return

    print("\n🔍 Looking up Gopi's VeterinaryStaff record...")
    staff, created = VeterinaryStaff.objects.get_or_create(
        auth_user_id=GOPI_AUTH_USER_ID,
        defaults={'role': 'DOCTOR'}
    )
    if created:
        print(f"✅ Created new VeterinaryStaff: {staff.auth_user_id}")
    else:
        print(f"ℹ️  Found existing VeterinaryStaff: {staff.auth_user_id}")

    print("\n🔍 Checking for existing StaffClinicAssignment...")
    existing = StaffClinicAssignment.objects.filter(staff=staff, clinic=clinic).first()
    if existing:
        print(f"ℹ️  StaffClinicAssignment already exists: role={existing.role}, is_active={existing.is_active}")
        if not existing.is_active:
            existing.is_active = True
            existing.save()
            print("✅ Re-activated the existing assignment.")
        return

    print("⚠️  No assignment found. Creating StaffClinicAssignment for Gopi as DOCTOR...")
    assignment = StaffClinicAssignment.objects.create(
        staff=staff,
        clinic=clinic,
        role='DOCTOR',
        permissions=['VETERINARY_CORE', 'VETERINARY_DOCTOR', 'VETERINARY_VISITS'],
        is_active=True,
        is_primary=True,
        specialization='General Veterinary',
        consultation_fee=0.00,
    )
    print(f"✅ Created StaffClinicAssignment: role={assignment.role}, clinic={clinic.name}, is_active={assignment.is_active}")
    print("\n✅ Fix complete! Gopi g is now an active DOCTOR in his clinic in veterinary_service.")
    print("Next: Run fix_gopi_schedule.py in service_provider_service to add an approved schedule.")

if __name__ == "__main__":
    fix_gopi_vet_assignment()
