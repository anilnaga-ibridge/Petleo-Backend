from .availability_service import AvailabilityService
from ..models import OrganizationEmployee

class OrganizationAvailabilityService:
    @staticmethod
    def get_org_available_slots(org_id, facility_id, date, consultation_type_id=None):
        """
        Aggregates available slots from all employees qualified for the given facility.
        Model 2: Service-First Booking.
        """
        # 1. Find qualified employees via EmployeeServiceMapping
        eligible_employees = OrganizationEmployee.objects.filter(
            organization_id=org_id,
            status='ACTIVE',
            service_mappings__facility_id=facility_id,
            service_mappings__is_active=True
        )
        
        # [NEW] Robustness Fallback:
        # If no specific employees are mapped to this service, 
        # assume all active employees of the organization can perform it.
        # This prevents "No slots available" errors when the provider forgets to map services.
        if not eligible_employees.exists():
            eligible_employees = OrganizationEmployee.objects.filter(
                organization_id=org_id,
                status='ACTIVE'
            )
            
        all_slots = set()
        for emp in eligible_employees:
            # Re-use the existing AvailabilityService for individual calculation
            emp_slots = AvailabilityService.get_available_slots(str(emp.auth_user_id), facility_id, date, consultation_type_id)
            all_slots.update(emp_slots)
            
        return sorted(list(all_slots))
