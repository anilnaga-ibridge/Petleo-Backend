import os
import django
import sys
from datetime import datetime, timedelta, time
from unittest import mock

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, OrganizationEmployee
from service_provider.models_scheduling import (
    EmployeeWorkingHours, EmployeeLeave, EmployeeDailySchedule,
    EmployeeBlockTime, ProviderResource, FacilityResourceConstraint
)
from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory, ProviderTemplateFacility
from service_provider.services.availability_service import AvailabilityService
from django.contrib.auth.models import User
from django.db import transaction

def test_availability_logic():
    print("--- Starting Availability Logic Unit Tests ---")
    
    # 1. Setup Test Data
    with transaction.atomic():
        # Clean up
        ServiceProvider.objects.filter(providerName='TestAvailabilityClinic').delete()
        ProviderTemplateService.objects.filter(name='TestService').delete()
        
        provider = ServiceProvider.objects.create(
            providerName='TestAvailabilityClinic',
            providerType='ORGANIZATION',
            is_active=True,
            status='ACTIVE'
        )
        
        user_doc = User.objects.create(username='avail_doc', email='avail@test.com')
        doc = OrganizationEmployee.objects.create(
            organization=provider,
            auth_user_id=str(user_doc.id),
            full_name='Availability Doctor',
            status='ACTIVE'
        )
        
        # Setup Template Structure
        ts = ProviderTemplateService.objects.create(name='TestService', display_name='Test Service')
        tc = ProviderTemplateCategory.objects.create(
            service=ts, 
            name='TestCat', 
            super_admin_category_id='cat-123',
            duration_minutes=45, # Phase 3: Category owns duration
            base_price=100.00
        )
        facility = ProviderTemplateFacility.objects.create(
            category=tc, 
            name='TestFac', 
            super_admin_facility_id='fac-123',
            buffer_minutes=0,
            slot_granularity=15
        )
        
        # Setup Working Hours: 09:00 - 12:00
        target_date = datetime.now().date() + timedelta(days=1)
        while target_date.weekday() > 4: # Ensure it's Mon-Fri
            target_date += timedelta(days=1)
            
        weekday = target_date.weekday()
        EmployeeWorkingHours.objects.create(
            employee=doc,
            day_of_week=weekday,
            start_time=time(9, 0),
            end_time=time(12, 0),
            break_start=time(10, 30),
            break_end=time(11, 0)
        )

        print(f"[TEST 1] Testing Basic Availability (Working Hours + Breaks)...")
        # Mock Cache & Locks to isolate logic
        with mock.patch('service_provider.services.cached_slots.AvailabilityCacheService.get_slots', return_value=None):
            with mock.patch('service_provider.services.cached_slots.AvailabilityCacheService.set_slots'):
                with mock.patch('service_provider.services.slot_lock.SlotLockService.is_locked', return_value=False):
                    with mock.patch('service_provider.services.availability_service.AvailabilityService._get_confirmed_bookings', return_value=[]):
                        slots = AvailabilityService.get_available_slots(str(doc.auth_user_id), facility.id, target_date)
                        print(f"   Generated slots: {slots}")
                        # Expected: 09:00, 09:15, 09:30, 09:45 (since duration is 45 and break at 10:30)
                        # Actually 09:00 (ends 09:45), 09:15 (ends 10:00), 09:30 (ends 10:15), 09:45 (ends 10:30)
                        # 10:00 would end at 10:45 which overlaps break.
                        assert "09:00" in slots
                        assert "09:45" in slots
                        assert "10:00" not in slots
                        print("   SUCCESS: Basic availability verified.")

        print(f"[TEST 2] Testing Partial Leave Overlap...")
        EmployeeLeave.objects.create(
            employee=doc,
            date=target_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status='APPROVED'
        )
        with mock.patch('service_provider.services.cached_slots.AvailabilityCacheService.get_slots', return_value=None):
            with mock.patch('service_provider.services.cached_slots.AvailabilityCacheService.set_slots'):
                with mock.patch('service_provider.services.slot_lock.SlotLockService.is_locked', return_value=False):
                    with mock.patch('service_provider.services.availability_service.AvailabilityService._get_confirmed_bookings', return_value=[]):
                        slots = AvailabilityService.get_available_slots(str(doc.auth_user_id), facility.id, target_date)
                        print(f"   Generated slots after partial leave: {slots}")
                        # Slots shouldn't start before 09:30
                        assert "09:00" not in slots
                        assert "09:15" not in slots
                        assert "09:30" in slots
                        print("   SUCCESS: Partial leave overlap verified.")

        print(f"[TEST 3] Testing Resource Constraints (Multi-Room/Equipment)...")
        res = ProviderResource.objects.create(provider=provider, name='OP-Room-1', resource_type='ROOM')
        FacilityResourceConstraint.objects.create(facility=facility, resource=res)
        
        # Mock occupied resource (Simulate another doctor using the room)
        mock_occupancy = [{
            'resource_id': str(res.id),
            'start': datetime.combine(target_date, time(9, 30)),
            'end': datetime.combine(target_date, time(10, 0))
        }]
        
        with mock.patch('service_provider.services.cached_slots.AvailabilityCacheService.get_slots', return_value=None):
            with mock.patch('service_provider.services.cached_slots.AvailabilityCacheService.set_slots'):
                with mock.patch('service_provider.services.slot_lock.SlotLockService.is_locked', return_value=False):
                    with mock.patch('service_provider.services.availability_service.AvailabilityService._get_confirmed_bookings', return_value=[]):
                        with mock.patch('service_provider.services.availability_service.AvailabilityService._get_provider_resource_occupancy', return_value=mock_occupancy):
                            slots = AvailabilityService.get_available_slots(str(doc.auth_user_id), facility.id, target_date)
                            print(f"   Generated slots after resource block: {slots}")
                            # 09:30 slot ends at 10:15, overlaps with resource block 09:30-10:00.
                            assert "09:30" not in slots
                            print("   SUCCESS: Resource constraints verified.")

        raise Exception("Rollback test data")

if __name__ == "__main__":
    try:
        test_availability_logic()
    except Exception as e:
        if str(e) == "Rollback test data":
            print("\nALL TESTS PASSED SUCCESSFULLY!")
        else:
            print(f"\nTests FAILED: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
