import os
import django
import sys
from datetime import datetime, timedelta

# Setup Django environment for service_provider_service
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, OrganizationEmployee
try:
    from service_provider.models import OrganizationEmployeeServiceMapping
except ImportError:
    from service_provider.models import EmployeeServiceMapping as OrganizationEmployeeServiceMapping
from service_provider.models_scheduling import EmployeeAvailability
from service_provider.services.smart_assignment_service import SmartAssignmentService
from django.contrib.auth.models import User
from django.db import transaction

def verify_smart_assignment():
    print("--- Starting Model 2: Smart Assignment Verification ---")
    
    # 1. Setup Test Data
    with transaction.atomic():
        # Clean up existing if any
        ServiceProvider.objects.filter(providerName='SmartClinic').delete()
        
        clinic = ServiceProvider.objects.create(
            providerName='SmartClinic',
            providerType='ORGANIZATION',
            is_active=True,
            status='ACTIVE'
        )
        
        # Service setup
        facility_id = 'test-spa'
        
        # Doctor A: Rating 4.5
        user_a = User.objects.create(username='doc_a_smart', email='a@smart.com')
        doc_a = OrganizationEmployee.objects.create(
            organization=clinic,
            auth_user_id=user_a.id,
            full_name='Doctor A',
            average_rating=4.5,
            status='ACTIVE'
        )
        OrganizationEmployeeServiceMapping.objects.create(employee=doc_a, facility_id=facility_id, is_active=True)
        
        # Doctor B: Rating 4.8
        user_b = User.objects.create(username='doc_b_smart', email='b@smart.com')
        doc_b = OrganizationEmployee.objects.create(
            organization=clinic,
            auth_user_id=user_b.id,
            full_name='Doctor B',
            average_rating=4.8,
            status='ACTIVE'
        )
        OrganizationEmployeeServiceMapping.objects.create(employee=doc_b, facility_id=facility_id, is_active=True)

        target_date = datetime.now().date()
        target_time = "10:00"
        
        print(f"[Step 1] Verifying Equal Workload -> Highest Rating Wins...")
        # Mock availability for both
        import unittest.mock as mock
        with mock.patch('service_provider.services.availability_service.AvailabilityService.get_available_slots', return_value=[target_time]):
            with mock.patch('service_provider.services.availability_service.AvailabilityService._get_confirmed_bookings', return_value=[]):
                assigned = SmartAssignmentService.assign_employee_for_slot(clinic.id, facility_id, str(target_date), target_time)
                print(f"   Assigned: {assigned.full_name} (Expected: Doctor B due to 4.8 vs 4.5)")
                assert assigned.id == doc_b.id

        print(f"[Step 2] Verifying Workload Priority -> Least Busy Wins...")
        # Mock: Doc B is busy (1 booking), Doc A is free (0 bookings)
        def mock_bookings(auth_id, date):
            if str(auth_id) == str(doc_b.auth_user_id):
                return [1] # Doc B has one booking
            return [] # Doc A has none
            
        with mock.patch('service_provider.services.availability_service.AvailabilityService.get_available_slots', return_value=[target_time]):
            with mock.patch('service_provider.services.availability_service.AvailabilityService._get_confirmed_bookings', side_effect=mock_bookings):
                assigned = SmartAssignmentService.assign_employee_for_slot(clinic.id, facility_id, str(target_date), target_time)
                print(f"   Assigned: {assigned.full_name} (Expected: Doctor A because B is busy)")
                assert assigned.id == doc_a.id

        print("\nSUCCESS: Smart Assignment Logic Verified (Workload > Rating)")

if __name__ == "__main__":
    try:
        verify_smart_assignment()
    except Exception as e:
        print(f"Verification FAILED: {e}")
        import traceback
        traceback.print_exc()
