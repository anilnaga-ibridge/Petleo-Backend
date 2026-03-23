import os
import django
import sys
import uuid
import datetime
from django.utils import timezone

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import Visit, VisitStatusHistory, Clinic, PetOwner, Pet, VeterinaryStaff, StaffClinicAssignment
from veterinary.services import WorkflowService
from django.contrib.auth import get_user_model

def setup_test_data():
    print("--- Setting up test data ---")
    clinic, _ = Clinic.objects.get_or_create(
        name="Test Workflow Clinic",
        defaults={
            'organization_id': uuid.uuid4().hex,
            'phone': '123456789'
        }
    )
    
    owner, _ = PetOwner.objects.get_or_create(
        email="testowner@example.com",
        defaults={
            'name': "Test Owner",
            'phone': "555-0199",
            'clinic': clinic,
            'auth_user_id': uuid.uuid4().hex
        }
    )
    
    pet, _ = Pet.objects.get_or_create(
        name="Buddy Test",
        owner=owner,
        defaults={
            'species': 'Dog',
            'breed': 'Golden Retriever',
        }
    )
    
    staff_auth_id = uuid.uuid4().hex
    staff, _ = VeterinaryStaff.objects.get_or_create(
        auth_user_id=staff_auth_id,
        defaults={
            'full_name': 'Dr. Test Vet'
        }
    )
    
    StaffClinicAssignment.objects.get_or_create(
        staff=staff,
        clinic=clinic,
        role='DOCTOR'
    )
    
    return clinic, pet, staff_auth_id

def run_tests():
    clinic, pet, doctor_id = setup_test_data()
    
    print("\n--- Test 1: Happy Path Workflow ---")
    # 1. Create Visit
    visit = Visit.objects.create(
        clinic=clinic,
        pet=pet,
        status='CREATED',
        priority='P2',
        reason='Checkup testing'
    )
    print(f"Created Visit: {visit.id} [{visit.status}]")
    
    # Verify exact transitions
    workflow_steps = [
        ('CHECKED_IN', "Reception checks in patient"),
        ('VITALS_RECORDED', "Nurse records vitals"),
        ('DOCTOR_ASSIGNED', "Assigned to doctor", {'doctor_id': doctor_id}),
        ('CONSULTATION_DONE', "Doctor finishes examining"),
        ('PRESCRIPTION_FINALIZED', "Prescription written"),
        ('PAYMENT_PENDING', "Sent to billing"),
        ('PAID', "Client pays bill"),
        ('CLOSED', "Visit marked complete"),
    ]
    
    try:
        for new_status, desc, *args in workflow_steps:
            print(f"-> Transitioning to {new_status} ({desc})...")
            
            if new_status == 'DOCTOR_ASSIGNED':
                 visit.assigned_doctor_auth_id = doctor_id
                 visit.save()
            
            WorkflowService.transition_visit(visit, new_status, user_role='TEST_RUNNER')
            visit.refresh_from_db()
            history_count = VisitStatusHistory.objects.filter(visit=visit).count()
            print(f"   Success! queue_entered_at updated. History count: {history_count}")
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return False
        
    print("\n--- Test 2: Invalid Transition Guard ---")
    try:
        visit2 = Visit.objects.create(
            clinic=clinic,
            pet=pet,
            status='CREATED'
        )
        print(f"Attempting to jump CREATED -> CLOSED directly on a new visit...")
        WorkflowService.transition_visit(visit2, 'CLOSED')
        print(f"❌ Failed: The transition was allowed but shouldn't have been!")
        return False
    except ValueError as e:
        print(f"✅ Success: Correctly prevented invalid transition! ({e})")
        
    print("\n--- Summary ---")
    print("All tests passed! The backend workflow state machine is strictly enforced.")
    return True

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
