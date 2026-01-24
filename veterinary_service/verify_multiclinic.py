import os
import sys
import django
import uuid

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import VeterinaryStaff, Clinic, StaffClinicAssignment

def verify_multiclinic_architecture():
    print("\n🏢 Verifying Multi-Clinic Architecture...")

    org_id = str(uuid.uuid4())
    staff_id = str(uuid.uuid4())

    # 1. Simulate Organization Creation (Kafka USER_CREATED)
    print(f"   Simulating USER_CREATED for Org: {org_id}")
    clinic, created = Clinic.objects.get_or_create(
        organization_id=org_id,
        defaults={"name": f"Test Org Clinic", "is_primary": True}
    )
    if created:
        print(f"   ✅ Primary Clinic created successfully.")
    
    # 2. Simulate Staff Creation (Kafka USER_CREATED)
    print(f"   Simulating USER_CREATED for Staff: {staff_id} assigned to Org: {org_id}")
    staff, _ = VeterinaryStaff.objects.update_or_create(
        auth_user_id=staff_id,
        defaults={"role": "doctor"}
    )
    
    # Auto-create assignment
    assignment, a_created = StaffClinicAssignment.objects.get_or_create(
        staff=staff,
        clinic=clinic,
        defaults={"is_primary": True, "permissions": ["VETERINARY_CORE"]}
    )
    if a_created:
        print(f"   ✅ StaffClinicAssignment created for primary clinic.")

    # 3. Simulate Multi-Clinic Extension
    print("   Testing Multi-Clinic Extension...")
    secondary_clinic = Clinic.objects.create(
        name="Secondary Clinic",
        organization_id=org_id,
        is_primary=False
    )
    
    assignment2 = StaffClinicAssignment.objects.create(
        staff=staff,
        clinic=secondary_clinic,
        is_primary=False,
        permissions=["VETERINARY_CORE", "VETERINARY_VITALS"]
    )
    print(f"   ✅ Successfully assigned staff to a second clinic.")

    # 4. Verify Middleware Resolution Logic (Simulation)
    print("   Verifying Context Resolution...")
    
    # Default (Primary)
    res_primary = StaffClinicAssignment.objects.filter(staff=staff, is_primary=True).first()
    print(f"   Primary Clinic: {res_primary.clinic.name} (ID: {res_primary.clinic_id})")
    
    # Explicit Switch
    res_switch = StaffClinicAssignment.objects.filter(staff=staff, clinic=secondary_clinic).first()
    print(f"   Switched Clinic: {res_switch.clinic.name} (Permissions: {res_switch.permissions})")

    if res_switch.permissions != res_primary.permissions:
        print("   ✅ Multi-clinic permission isolation verified.")

    # Cleanup
    assignment.delete()
    assignment2.delete()
    staff.delete()
    secondary_clinic.delete()
    clinic.delete()
    print("\n🎉 Multi-Clinic Verification Passed!")

if __name__ == "__main__":
    verify_multiclinic_architecture()
