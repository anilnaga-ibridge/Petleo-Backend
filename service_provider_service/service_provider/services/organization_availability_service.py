from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import logging
from .availability_service import AvailabilityService
from ..models import OrganizationEmployee, OrganizationAvailability
from ..models_scheduling import ProviderResource

logger = logging.getLogger(__name__)

class OrganizationAvailabilityService:
    @staticmethod
    def get_org_available_slots(org_id, facility_id, date, consultation_type_id=None):
        """
        Aggregates slots from both Employee Layer (Tier 1) and Clinic Fallback Layer (Tier 2).
        Model 2: Service-First Booking with Safeguards.
        """
        # --- PHASE 0: PREPARATION ---
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()
            
        # --- PHASE 1: TIER 1 (EMPLOYEES) ---
        eligible_employees = OrganizationEmployee.objects.filter(
            organization_id=org_id,
            status='ACTIVE',
            service_mappings__facility_id=facility_id,
            service_mappings__is_active=True
        )
        
        tier1_slots = {} # time -> slot_info

        def fetch_emp_slots(emp):
            return AvailabilityService.get_available_slots(
                str(emp.auth_user_id), 
                facility_id, 
                date, 
                consultation_type_id
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_emp_slots, eligible_employees)
            for emp_slots in results:
                for time_str in emp_slots:
                    if time_str not in tier1_slots:
                        tier1_slots[time_str] = {
                            "time": time_str,
                            "tier": 1,
                            "type": "INSTANT_CONFIRMED"
                        }

        # --- PHASE 2: TIER 2 (CLINIC FALLBACK) ---
        tier2_slots = {}
        fallback_cfg = OrganizationAvailability.objects.filter(
            organization_id=org_id,
            day_of_week=date.weekday(),
            fallback_enabled=True
        ).first()

        if fallback_cfg:
            # Generate potential fallback slots
            current_dt = datetime.combine(date, fallback_cfg.start_time)
            end_dt = datetime.combine(date, fallback_cfg.end_time)
            duration = fallback_cfg.slot_duration_minutes
            
            # Basic slot generation
            potential_t2 = []
            while current_dt + timedelta(minutes=duration) <= end_dt:
                potential_t2.append(current_dt)
                current_dt += timedelta(minutes=15) # 15m granularity
            
            # Resource-Aware Capacity Check
            resource_usage = AvailabilityService._get_provider_resource_occupancy(str(org_id), date)
            
            for slot_start in potential_t2:
                time_str = slot_start.strftime('%H:%M')
                
                # Deduplication: Prefer Tier 1 (Rule 8)
                if time_str in tier1_slots:
                    continue
                
                slot_end = slot_start + timedelta(minutes=duration)
                
                # Check 1: Static Org Capacity/Resource Counting
                total_at_time = 0
                for usage in resource_usage:
                     if slot_start < usage['end'] and slot_end > usage['start']:
                         total_at_time += 1
                
                if total_at_time < fallback_cfg.capacity:
                    tier2_slots[time_str] = {
                        "time": time_str,
                        "tier": 2,
                        "type": "REQUEST_REQUIRED" # Rule 7
                    }

        # --- PHASE 3: MERGE & SORT ---
        merged = {**tier2_slots, **tier1_slots} # Tier 1 overwrites Tier 2 duplicate keys
        
        final_list = sorted(merged.values(), key=lambda x: x['time'])
        
        # --- PHASE 4: WAITLIST DETECTION (Tier 3) ---
        # If no slots found but fallback is enabled, suggest waitlist (Rule 4)
        waitlist_available = False
        if not final_list and fallback_cfg:
            waitlist_available = True
            
        return {
            "slots": final_list,
            "waitlist_available": waitlist_available,
            "tier2_enabled": bool(fallback_cfg)
        }
