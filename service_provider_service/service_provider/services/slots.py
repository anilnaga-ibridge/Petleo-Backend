import logging
from datetime import datetime, timedelta, time
from django.utils import timezone
from service_provider.models_scheduling import EmployeeWorkingHours, EmployeeLeave
from provider_dynamic_fields.models import ProviderFacility

logger = logging.getLogger(__name__)

class SlotGenerationService:
    """
    Engine for generating available booking slots dynamically.
    No slots are stored in the database.
    """

    @staticmethod
    def generate_slots(employee_id, facility_id, target_date):
        """
        Generate a list of available slots for a specific employee, facility, and date.
        
        Args:
            employee_id (UUID): The ID of the employee.
            facility_id (UUID): The ID of the facility/service.
            target_date (date): The date to generate slots for.
            
        Returns:
            list: A list of dicts containing start_time and end_time for each available slot.
        """
        try:
            facility = ProviderFacility.objects.get(id=facility_id)
            duration = facility.duration_minutes
            buffer = facility.buffer_minutes
            granularity = facility.slot_granularity or 15
            total_block = duration + buffer
            
            # 1. Fetch Working Hours
            weekday = target_date.weekday() # 0 = Monday
            working_hours = EmployeeWorkingHours.objects.filter(
                employee_id=employee_id, 
                day_of_week=weekday, 
                is_active=True
            ).first()
            
            if not working_hours:
                return []

            # 2. Check for Full Day Leave
            full_day_leave = EmployeeLeave.objects.filter(
                employee_id=employee_id,
                date=target_date,
                status='APPROVED',
                start_time__isnull=True
            ).exists()
            
            if full_day_leave:
                return []

            # 3. Initialize Working Range
            day_start = datetime.combine(target_date, working_hours.start_time)
            day_end = datetime.combine(target_date, working_hours.end_time)
            
            # 4. Filter by Partial Leaves
            partial_leaves = EmployeeLeave.objects.filter(
                employee_id=employee_id,
                date=target_date,
                status='APPROVED',
                start_time__isnull=False
            )
            
            # 5. TODO: Fetch Existing Bookings from Customer Service
            # For now, we assume an empty booking list or use a local mock for testing.
            # In production, this would be a Cross-Service request or a synced table.
            bookings = [] 

            # 6. Slot Generation Algorithm
            slots = []
            current_time = day_start
            
            while current_time + timedelta(minutes=duration) <= day_end:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=duration)
                
                # Check for Break
                is_in_break = False
                if working_hours.break_start and working_hours.break_end:
                    b_start = datetime.combine(target_date, working_hours.break_start)
                    b_end = datetime.combine(target_date, working_hours.break_end)
                    if not (slot_end <= b_start or slot_start >= b_end):
                        is_in_break = True
                
                # Check for Leave conflict
                is_on_leave = False
                for leave in partial_leaves:
                    l_start = datetime.combine(target_date, leave.start_time)
                    l_end = datetime.combine(target_date, leave.end_time)
                    if not (slot_end <= l_start or slot_start >= l_end):
                        is_on_leave = True
                        break

                # Check for Booking conflict
                is_booked = False
                for b in bookings:
                    if not (slot_end <= b['start'] or slot_start >= b['end']):
                        is_booked = True
                        break
                
                if not (is_in_break or is_on_leave or is_booked):
                    slots.append({
                        'start_time': slot_start.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                    })
                
                # Advance by granularity
                current_time += timedelta(minutes=granularity)
                
            return slots

        except Exception as e:
            logger.error(f"Error generating slots: {e}")
            return []
