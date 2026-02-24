import requests
import logging
from .models import BookingItem

logger = logging.getLogger(__name__)

class CapacityService:
    @staticmethod
    def get_facility_capacity(provider_id, facility_id):
        """
        Placeholder for fetching capacity from service_provider_service.
        In production, this would be a cached Kafka value or API call.
        """
        # Defaulting to 1 for now if unknown
        return 1 

    @staticmethod
    def check_availability(provider_id, facility_id, selected_time):
        """
        Checks if a slot is available based on capacity.
        """
        capacity = CapacityService.get_facility_capacity(provider_id, facility_id)
        
        # Count confirmed/pending bookings for this slot
        existing_count = BookingItem.objects.filter(
            provider_id=provider_id,
            facility_id=facility_id,
            selected_time=selected_time,
            status__in=['PENDING', 'CONFIRMED']
        ).count()
        
        return existing_count < capacity

class AutoAssignmentService:
    @staticmethod
    def assign_employee(provider_id, facility_id, selected_time):
        """
        Calls service_provider_service to find an available employee.
        """
        try:
            url = f"http://localhost:8002/api/provider/availability/{provider_id}/assign-employee/"
            payload = {
                "selected_time": selected_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(selected_time, 'strftime') else selected_time,
                "facility_id": str(facility_id)
            }
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json().get('employee_id')
        except Exception as e:
            logger.error(f"Auto-assignment failed for provider {provider_id}: {e}")
        
        return None
