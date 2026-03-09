from concurrent.futures import ThreadPoolExecutor
from .availability_service import AvailabilityService
from ..models import OrganizationEmployee

class OrganizationAvailabilityService:
    @staticmethod
    def get_org_available_slots(org_id, facility_id, date, consultation_type_id=None):
        """
        Aggregates available slots from all employees qualified for the given facility.
        Model 2: Service-First Booking.
        Uses parallel computation for high performance.
        """
        # 1. Find qualified employees via EmployeeServiceMapping
        eligible_employees = OrganizationEmployee.objects.filter(
            organization_id=org_id,
            status='ACTIVE',
            service_mappings__facility_id=facility_id,
            service_mappings__is_active=True
        )
        
        # [NEW] Robustness Fallback
        if not eligible_employees.exists():
            eligible_employees = OrganizationEmployee.objects.filter(
                organization_id=org_id,
                status='ACTIVE'
            )
            
        all_slots = set()

        def fetch_slots(emp):
            return AvailabilityService.get_available_slots(
                str(emp.auth_user_id), 
                facility_id, 
                date, 
                consultation_type_id
            )

        # 2. Parallelize computation across multiple employees
        # max_workers can be adjusted based on server capabilities
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map returns an iterator that yields results in order
            results = executor.map(fetch_slots, eligible_employees)
            
            for emp_slots in results:
                all_slots.update(emp_slots)
            
        return sorted(list(all_slots))
