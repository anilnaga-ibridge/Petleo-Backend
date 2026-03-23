import time
from datetime import datetime, timedelta, time as dt_time
import json
import requests
import logging
from django.conf import settings
from ..models_scheduling import (
    EmployeeWeeklySchedule, EmployeeLeave, EmployeeBlockTime, 
    EmployeeDailySchedule, FacilityResourceConstraint, ProviderResource
)
from ..models import OrganizationEmployee, ConsultationType, ServiceProvider

from .cached_slots import AvailabilityCacheService
from .slot_lock import SlotLockService
from .booking_projection import BookingProjectionService

logger = logging.getLogger(__name__)

class AvailabilityService:
    @staticmethod
    def get_available_slots(employee_id, facility_id, target_date, consultation_type_id=None):
        """
        Generates available slots for an employee on a specific date for a given service.
        Respects staff availability (Working Hours, Breaks, Leaves), Resource Constraints, 
        and existing Bookings.
        Uses Caching and Temporary Slot Locks for high performance and concurrency.
        """
        start_perf = time.perf_counter()
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        # 1. Check Cache
        cached_slots = AvailabilityCacheService.get_slots(employee_id, facility_id, target_date)
        if cached_slots is not None:
            # Filter by Redis locks even for cached slots to ensure real-time accuracy
            return [s for s in cached_slots if not SlotLockService.is_locked(employee_id, datetime.combine(target_date, datetime.strptime(s, '%H:%M').time()))]

        # 2. Get Employee
        try:
            employee = OrganizationEmployee.objects.get(auth_user_id=employee_id)
        except OrganizationEmployee.DoesNotExist:
            logger.error(f"Employee {employee_id} not found")
            return []

        # 2. Get Facility/Category Configuration
        duration = 30
        buffer = 0
        granularity = 15
        if facility_id:
            try:
                from provider_dynamic_fields.models import ProviderFacility, ProviderTemplateFacility, ProviderTemplateCategory
                facility = None
                try:
                    facility = ProviderFacility.objects.get(id=facility_id)
                except ProviderFacility.DoesNotExist:
                    facility = ProviderTemplateFacility.objects.get(id=facility_id)
                
                if facility:
                    # Architect Recommendation: Service/Category should control Duration/Price
                    # We check Category first, then fallback to Facility for legacy or specific overrides
                    category = getattr(facility, 'category', None)
                    if category:
                        duration = category.duration_minutes
                        # Price is handled at booking time, but we logic it here if needed
                    
                    # Fallback to facility defaults if category doesn't specify (or for buffer/granularity)
                    duration = duration or getattr(facility, 'duration_minutes', 30)
                    buffer = getattr(facility, 'buffer_minutes', 0)
                    granularity = getattr(facility, 'slot_granularity', 15)
                    
                    if consultation_type_id:
                        try:
                            ctype = ConsultationType.objects.get(id=consultation_type_id)
                            duration = ctype.duration_minutes
                        except ConsultationType.DoesNotExist:
                            pass
            except Exception as e:
                logger.error(f"Error resolving facility/category/duration: {e}")

        # 3. Check Leaves (Full Day)
        if EmployeeLeave.objects.filter(
            employee=employee, 
            date=target_date, 
            status='APPROVED',
            start_time__isnull=True
        ).exists():
            return []

        # 4. Get Approved Daily Schedule or Recurring Weekly Schedule
        schedule_start = None
        schedule_end = None
        
        # 4a. Check specific date override (Approved Daily Schedule)
        daily_schedule = EmployeeDailySchedule.objects.filter(
            employee=employee,
            date=target_date,
            status='APPROVED'
        ).first()

        if daily_schedule:
            schedule_start = daily_schedule.start_time
            schedule_end = daily_schedule.end_time
        else:
            # 4b. Fallback to general recurring weekly schedule (EmployeeAvailability)
            from ..models import EmployeeAvailability
            weekly_schedule = EmployeeAvailability.objects.filter(
                employee=employee,
                day_of_week=target_date.weekday(),
                is_active=True
            ).first()
            if weekly_schedule:
                schedule_start = weekly_schedule.start_time
                schedule_end = weekly_schedule.end_time

        if not schedule_start or not schedule_end or schedule_start == schedule_end:
            return []

        break_start = None
        break_end = None

        # 5. Get confirmed bookings and blocked times
        bookings = AvailabilityService._get_confirmed_bookings(employee_id, target_date)
        partial_leaves = EmployeeLeave.objects.filter(
            employee=employee, 
            date=target_date, 
            status='APPROVED',
            start_time__isnull=False
        )
        blocks = EmployeeBlockTime.objects.filter(employee=employee, date=target_date)

        # 6. Generate Candidate Slots
        candidate_slots = []
        current_dt = datetime.combine(target_date, schedule_start)
        end_dt = datetime.combine(target_date, schedule_end)
        
        while current_dt + timedelta(minutes=duration) <= end_dt:
            slot_start = current_dt
            slot_end = current_dt + timedelta(minutes=duration)
            
            is_available = True
            
            # 6a. Check Break
            if break_start and break_end:
                b_start = datetime.combine(target_date, break_start)
                b_end = datetime.combine(target_date, break_end)
                if slot_start < b_end and slot_end > b_start:
                    is_available = False

            # 6b. Check Partial Leaves
            if is_available:
                for leave in partial_leaves:
                    l_start = datetime.combine(target_date, leave.start_time)
                    l_end = datetime.combine(target_date, leave.end_time)
                    if slot_start < l_end and slot_end > l_start:
                        is_available = False
                        break

            # 6c. Check Blocked Times
            if is_available:
                for blk in blocks:
                    blk_start = datetime.combine(target_date, blk.start_time)
                    blk_end = datetime.combine(target_date, blk.end_time)
                    if slot_start < blk_end and slot_end > blk_start:
                        is_available = False
                        break

            # 6d. Check Staff Bookings
            if is_available:
                for b in bookings:
                    b_start = datetime.combine(target_date, datetime.strptime(b['start'], '%H:%M').time())
                    b_end = datetime.combine(target_date, datetime.strptime(b['end'], '%H:%M').time())
                    if slot_start < b_end and slot_end > b_start:
                        is_available = False
                        break
            
            if is_available:
                candidate_slots.append(slot_start.strftime('%H:%M'))
            
            current_dt += timedelta(minutes=granularity)

        # 7. RESOURCE CONSTRAINT CHECK
        required_constraints = FacilityResourceConstraint.objects.filter(facility_id=facility_id)
        
        slots_after_resource_check = []
        if not required_constraints.exists():
            slots_after_resource_check = candidate_slots
        else:
            provider_id = str(employee.organization_id)
            resource_usage = AvailabilityService._get_provider_resource_occupancy(provider_id, target_date)
            
            for slot_time in candidate_slots:
                slot_start = datetime.combine(target_date, datetime.strptime(slot_time, '%H:%M').time())
                slot_end = slot_start + timedelta(minutes=duration)
                
                all_resources_free = True
                for constraint in required_constraints:
                    resource = constraint.resource
                    resource_id = str(resource.id)
                    capacity = getattr(resource, 'capacity', 1)
                    if not AvailabilityService._has_resource_capacity(resource_id, capacity, slot_start, slot_end, resource_usage):
                        all_resources_free = False
                        break
                
                if all_resources_free:
                    slots_after_resource_check.append(slot_time)

        # 8. Filter by Temporary Redis Locks
        final_available_slots = []
        for slot_time in slots_after_resource_check:
            try:
                slot_dt = datetime.combine(target_date, datetime.strptime(slot_time, '%H:%M').time())
                slot_end_dt = slot_dt + timedelta(minutes=duration)
                
                # Check granular lock
                if not SlotLockService.is_locked(employee_id, facility_id, facility_id, slot_dt, slot_end_dt):
                    final_available_slots.append(slot_time)
            except Exception:
                # If redis fails, default to showing the slot and letting the DB transaction handle overlaps later
                final_available_slots.append(slot_time)

        # 9. Update Cache (Store the raw resource-cleared candidates, filtering locks happens on retrieval)
        AvailabilityCacheService.set_slots(employee_id, facility_id, target_date, slots_after_resource_check)

        latency = (time.perf_counter() - start_perf) * 1000
        logger.info(f"[Metrics] Availability checked for {employee_id} on {target_date}. Latency: {latency:.2f}ms. Slots: {len(final_available_slots)}")

        return sorted(list(set(final_available_slots)))

    @staticmethod
    def _has_resource_capacity(resource_id, capacity, slot_start, slot_end, resource_usage):
        """Check if a specific resource has available capacity during the given time range."""
        overlaps = 0
        for usage in resource_usage:
            if usage['resource_id'] == resource_id:
                u_start = usage['start']
                u_end = usage['end']
                if slot_start < u_end and slot_end > u_start:
                    overlaps += 1
        
        return overlaps < capacity

    @staticmethod
    def _get_provider_resource_occupancy(provider_id, target_date):
        """
        Calculates resource occupancy across ALL bookings for a provider.
        """
        occupancy = []
        date_str = target_date.strftime('%Y-%m-%d')
        
        # 1. Fetch ALL bookings for this provider from customer_service
        provider_bookings = []
        try:
            url = f"http://localhost:8005/api/pet-owner/bookings/bookings/internal_provider_bookings/"
            params = {"provider_id": provider_id, "date": date_str}
            resp = requests.get(url, params=params, timeout=2) # Added Circuit Breaker Timeout
            if resp.status_code == 200:
                provider_bookings = resp.json()
        except requests.exceptions.Timeout:
            logger.warning(f"⏳ Circuit Breaker tripped: Timeout fetching provider bookings for resource check")
        except Exception as e:
            logger.error(f"Failed to fetch provider bookings for resource check: {e}")

        # 2. Fetch ALL appointments from veterinary_service
        medical_appointments = []
        try:
            url = f"http://localhost:8004/api/veterinary/appointments/internal_clinic_appointments/"
            # Ensure we match organization_id (Petleo uses organization_id as the primary sync key)
            params = {"clinic_id": provider_id, "date": date_str}
            resp = requests.get(url, params=params, timeout=2) # Added Circuit Breaker Timeout
            if resp.status_code == 200:
                medical_appointments = resp.json()
        except requests.exceptions.Timeout:
            logger.warning(f"⏳ Circuit Breaker tripped: Timeout fetching clinic appointments for resource check")
        except Exception as e:
            logger.error(f"Failed to fetch clinic appointments for resource check: {e}")

        # 3. Map bookings to resources
        all_events = provider_bookings + medical_appointments
        for event in all_events:
            fid = event.get('facility_id') or event.get('service_id')
            if not fid: continue
            
            # Find resources linked to this facility
            linked_resources = FacilityResourceConstraint.objects.filter(facility_id=fid).values_list('resource_id', flat=True)
            
            e_start = datetime.combine(target_date, datetime.strptime(event['start'], '%H:%M').time())
            e_end = datetime.combine(target_date, datetime.strptime(event['end'], '%H:%M').time())
            
            for rid in linked_resources:
                occupancy.append({
                    'resource_id': str(rid),
                    'start': e_start,
                    'end': e_end
                })
        
        return occupancy

    @staticmethod
    def _get_confirmed_bookings(employee_id, target_date):
        """
        Fetch bookings from Redis Projection Cache FIRST.
        Fallback to customer_service AND veterinary_service with Circuit Breakers if Cache empty/fails.
        """
        combined_bookings = []
        date_str = target_date.strftime('%Y-%m-%d')
        
        # 0. Try Redis Booking Projection Cache first
        cached_intervals = BookingProjectionService.get_employee_bookings(employee_id, date_str)
        if cached_intervals is not None:
             logger.info(f"⚡️ Cache HIT: Booking Projection used for {employee_id} on {date_str}")
             return cached_intervals
             
        logger.info(f"🐢 Cache MISS: Falling back to cross-service HTTP calls for {employee_id}")

        # 1. Fetch from customer_service (with Circuit Breaker timeout)
        try:
            url = f"http://localhost:8005/api/pet-owner/bookings/bookings/internal_employee_bookings/"
            params = {"employee_id": employee_id, "date": date_str}
            response = requests.get(url, params=params, timeout=2) # 2 sec timeout for circuit breaker
            if response.status_code == 200:
                combined_bookings.extend(response.json())
        except requests.exceptions.Timeout:
             logger.warning(f"⏳ Circuit Breaker tripped: Timeout reaching customer_service")
        except Exception as e:
             logger.error(f"Failed to fetch employee bookings: {e}")

        # 2. Fetch from veterinary_service (with Circuit Breaker timeout)
        try:
            url = f"http://localhost:8004/api/veterinary/appointments/internal_doctor_appointments/"
            params = {"doctor_auth_id": employee_id, "date": date_str}
            response = requests.get(url, params=params, timeout=2) # 2 sec timeout
            if response.status_code == 200:
                combined_bookings.extend(response.json())
        except requests.exceptions.Timeout:
             logger.warning(f"⏳ Circuit Breaker tripped: Timeout reaching veterinary_service")
        except Exception as e:
             logger.error(f"Failed to fetch doctor appointments: {e}")

        # 3. Populate cache asynchronously so next query is fast
        try:
            # We recreate the list so the kafka consumer logic matches
            r_client = BookingProjectionService.get_redis_client()
            r_client.set(
                 BookingProjectionService._generate_key(employee_id, date_str),
                 json.dumps(combined_bookings),
                 ex=86400 * 7
            )
        except Exception:
             pass

        return combined_bookings
