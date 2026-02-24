from datetime import datetime, timedelta, time
import requests
import logging
from django.conf import settings
from ..models_scheduling import EmployeeWeeklySchedule, EmployeeLeave, EmployeeBlockTime, EmployeeDailySchedule
from ..models import OrganizationEmployee, ConsultationType
from provider_dynamic_fields.models import ProviderTemplateFacility

logger = logging.getLogger(__name__)

class AvailabilityService:
    @staticmethod
    def get_available_slots(employee_id, facility_id, target_date, consultation_type_id=None):
        """
        Generates available slots for an employee on a specific date for a given service.
        """
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        weekday = target_date.weekday()
        
        # 1. Get Employee
        try:
            employee = OrganizationEmployee.objects.get(auth_user_id=employee_id)
        except OrganizationEmployee.DoesNotExist:
            logger.error(f"Employee {employee_id} not found")
            return []

        # 2. Check Leaves
        if EmployeeLeave.objects.filter(employee=employee, date=target_date).exists():
            return []

        # 3. Get Availability (Prioritize Daily Schedule, Fallback to Weekly)
        daily_schedule = EmployeeDailySchedule.objects.filter(
            employee=employee,
            date=target_date,
            status='APPROVED'
        ).first()

        if daily_schedule:
            schedule_start = daily_schedule.start_time
            schedule_end = daily_schedule.end_time
            # If start and end are same, it's a day off
            if schedule_start == schedule_end:
                return []
        else:
            # Fallback to Weekly Recurring Schedule
            weekly_schedule = EmployeeWeeklySchedule.objects.filter(
                employee=employee, 
                day_of_week=weekday, 
                status='APPROVED'
            ).first()
            
            if not weekly_schedule:
                return []
            
            schedule_start = weekly_schedule.start_time
            schedule_end = weekly_schedule.end_time

        # 4. Get Service Duration
        duration = 60 # Default
        try:
            if consultation_type_id:
                try:
                    ctype = ConsultationType.objects.get(id=consultation_type_id)
                    duration = ctype.duration_minutes
                except ConsultationType.DoesNotExist:
                    logger.warning(f"ConsultationType {consultation_type_id} not found, falling back to facility duration")
                    facility = ProviderTemplateFacility.objects.get(id=facility_id)
                    duration = facility.default_duration_minutes
            else:
                facility = ProviderTemplateFacility.objects.get(id=facility_id)
                duration = facility.default_duration_minutes
        except Exception as e:
            logger.error(f"Error resolving duration: {e}")

        # 5. Get confirmed bookings from customer_service
        bookings = AvailabilityService._get_confirmed_bookings(employee_id, target_date)
        
        # 6. Get Blocked Times
        blocks = EmployeeBlockTime.objects.filter(employee=employee, date=target_date)

        # 7. Generate possible slots
        slots = []
        current_dt = datetime.combine(target_date, schedule_start)
        end_dt = datetime.combine(target_date, schedule_end)
        
        buffer_minutes = 30
        
        while current_dt + timedelta(minutes=duration) <= end_dt:
            slot_start = current_dt
            slot_end = current_dt + timedelta(minutes=duration)
            
            # Check overlap with bookings (+ buffer)
            is_available = True
            
            # 7a. Check Bookings
            for b in bookings:
                # Booking object expected: {'start': 'HH:MM', 'end': 'HH:MM'}
                b_start = datetime.combine(target_date, datetime.strptime(b['start'], '%H:%M').time())
                b_end = datetime.combine(target_date, datetime.strptime(b['end'], '%H:%M').time())
                
                # Buffer logic: Booking occupies its time + 30 mins buffer
                total_occupied_end = b_end + timedelta(minutes=buffer_minutes)
                
                # Standard overlap check: (StartA < EndB) and (EndA > StartB)
                if slot_start < total_occupied_end and slot_end > b_start:
                    is_available = False
                    break
            
            if not is_available:
                # Simply move forward by the smallest granularity
                current_dt += timedelta(minutes=15)
                continue

            # 7b. Check Blocked Times
            for blk in blocks:
                blk_start = datetime.combine(target_date, blk.start_time)
                blk_end = datetime.combine(target_date, blk.end_time)
                if slot_start < blk_end and slot_end > blk_start:
                    is_available = False
                    break
            
            if is_available:
                slots.append(slot_start.strftime('%H:%M'))
                # Move forward for next possible slot
                current_dt += timedelta(minutes=15)
            else:
                current_dt += timedelta(minutes=15)

        return sorted(list(set(slots)))

    @staticmethod
    def _get_confirmed_bookings(employee_id, target_date):
        """
        Fetch bookings from customer_service AND medical appointments from veterinary_service.
        """
        combined_bookings = []
        date_str = target_date.strftime('%Y-%m-%d')
        
        # 1. Fetch from customer_service (Port 8005)
        try:
            url = f"http://localhost:8005/api/pet-owner/bookings/bookings/internal_employee_bookings/"
            params = {"employee_id": employee_id, "date": date_str}
            response = requests.get(url, params=params, timeout=3)
            if response.status_code == 200:
                combined_bookings.extend(response.json())
        except Exception as e:
            logger.error(f"Failed to fetch customer bookings: {e}")

        # 2. Fetch from veterinary_service (Port 8004)
        try:
            url = f"http://localhost:8004/api/veterinary/appointments/internal_doctor_appointments/"
            params = {"doctor_auth_id": employee_id, "date": date_str}
            response = requests.get(url, params=params, timeout=3)
            if response.status_code == 200:
                combined_bookings.extend(response.json())
        except Exception as e:
            logger.error(f"Failed to fetch medical appointments: {e}")

        return combined_bookings
