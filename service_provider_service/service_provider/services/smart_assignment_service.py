import logging
from django.db import transaction
from .availability_service import AvailabilityService
from ..models import OrganizationEmployee

logger = logging.getLogger(__name__)


class SmartAssignmentService:
    """
    Intelligently assigns the best available employee for a booking slot.

    Assignment tiers (tried in order, falls back to next if no candidates found):

    Tier 1 - Explicit Service Mapping:
        Employee has a direct EmployeeServiceMapping row for this facility.
        Most specific — provider has manually said "this employee does this service".

    Tier 2 - Role Capability Match:
        Employee's assigned ProviderRole has a capability key that matches the
        booked service/category.

        Resolution chain:
          facility → ProviderTemplateFacility.required_capability
                   OR category.linked_capability
                   OR service name → guess capability key
          → ProviderRoleCapability.capability_key == resolved key
          → ProviderRole → OrganizationEmployee

        This means providers can create a role called "Pet Care Specialist",
        assign DAY_CARE capability, and any booking for Day Care services will
        automatically land on employees with that role.

    Tier 3 - All Active Employees:
        Final fallback.  Used when no specific mapping or role match exists.
        Ensures bookings are never rejected due to missing configuration.

    Within each tier, candidates are sorted by:
      1. booking_count ASC (least busy first)
      2. average_rating DESC (best rated among equally busy)
    """

    @staticmethod
    @transaction.atomic
    def assign_employee_for_slot(org_id, facility_id, date, start_time_str):
        """
        Returns the best OrganizationEmployee for the given org/facility/date/time,
        or None if absolutely no one is available.
        """
        # ── Resolve capability key for Tier 2 ─────────────────────────────────
        capability_key = SmartAssignmentService._resolve_capability_for_facility(facility_id)
        logger.info(f"[SmartAssign] org={org_id} facility={facility_id} capability={capability_key}")

        # ── Tier 1: Explicit service mapping ──────────────────────────────────
        candidates = SmartAssignmentService._get_mapped_candidates(
            org_id, facility_id, date, start_time_str
        )
        tier = 1

        # ── Tier 2: Role capability match ─────────────────────────────────────
        if not candidates and capability_key:
            candidates = SmartAssignmentService._get_capability_candidates(
                org_id, capability_key, facility_id, date, start_time_str
            )
            tier = 2

        # ── Tier 3: All active employees ──────────────────────────────────────
        if not candidates:
            candidates = SmartAssignmentService._get_all_active_candidates(
                org_id, facility_id, date, start_time_str
            )
            tier = 3

        if not candidates:
            logger.warning(f"[SmartAssign] No available candidates found after all tiers.")
            return None

        logger.info(f"[SmartAssign] Tier {tier} selected {len(candidates)} candidate(s). "
                    f"Picking best by least-busy + highest rating.")
        return candidates[0]['employee']

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_capability_for_facility(facility_id):
        """
        Determine the capability key that governs this facility.

        Resolution order:
        1. ProviderTemplateFacility.required_capability  (explicit, e.g. VETERINARY_DOCTOR)
        2. ProviderTemplateFacility.category.linked_capability (e.g. VETERINARY_VISITS)
        3. Service name → inferred capability key
           e.g.  "Pet Spa" → PET_SPA
                 "Day care" → DAY_CARE
                 "Grooming" → PET_GROOMING
        """
        if not facility_id:
            return None

        try:
            from provider_dynamic_fields.models import ProviderTemplateFacility
            # Try by local UUID first, then by super_admin_facility_id
            try:
                facility = ProviderTemplateFacility.objects.select_related(
                    'category', 'category__service'
                ).get(id=facility_id)
            except (ProviderTemplateFacility.DoesNotExist, Exception):
                facility = ProviderTemplateFacility.objects.select_related(
                    'category', 'category__service'
                ).get(super_admin_facility_id=str(facility_id))

            # 1. Facility-level explicit capability
            if facility.required_capability:
                return facility.required_capability

            # 2. Category-level linked capability
            if facility.category and facility.category.linked_capability:
                return facility.category.linked_capability

            # 3. Infer from service name → snake_upper
            if facility.category and facility.category.service:
                service_name = facility.category.service.name.strip().upper()
                # Common keyword mappings
                keyword_map = {
                    'SPA': 'PET_SPA',
                    'DAY CARE': 'DAY_CARE',
                    'DAYCARE': 'DAY_CARE',
                    'GROOMING': 'PET_GROOMING',
                    'TRAINING': 'PET_TRAINING',
                    'BOARDING': 'PET_BOARDING',
                    'VETERINARY': 'VETERINARY_CORE',
                }
                for keyword, cap in keyword_map.items():
                    if keyword in service_name:
                        return cap

                # Generic fallback: convert service name to capability-like key
                # "Pet Day Care" → PET_DAY_CARE
                inferred = service_name.replace(' ', '_').replace('-', '_')
                return inferred

        except Exception as e:
            logger.warning(f"[SmartAssign] Could not resolve capability for facility {facility_id}: {e}")

        return None

    @staticmethod
    def _score_candidates(employee_list, facility_id, date):
        """
        Given a list of OrganizationEmployee objects, return scored & sorted
        list of {'employee': emp, 'total_minutes': n, 'rating': r}.
        """
        from datetime import date as date_type, datetime as datetime_type
        if isinstance(date, str):
            date = datetime_type.strptime(date, '%Y-%m-%d').date()

        scored = []
        for emp in employee_list:
            bookings = AvailabilityService._get_confirmed_bookings(str(emp.auth_user_id), date)
            
            total_minutes = 0
            for b in bookings:
                try:
                    # Calculate duration from HH:MM strings
                    start = datetime_type.strptime(b['start'], '%H:%M')
                    end = datetime_type.strptime(b['end'], '%H:%M')
                    duration = (end - start).total_seconds() / 60
                    total_minutes += max(0, duration)
                except Exception:
                    # Fallback to a default duration if parsing fails
                    total_minutes += 30
            
            scored.append({
                'employee': emp,
                'total_minutes': total_minutes,
                'rating': float(emp.average_rating or 0),
            })
        # Least busy by minutes first, then highest rated
        scored.sort(key=lambda x: (x['total_minutes'], -x['rating']))
        return scored

    @staticmethod
    def _get_mapped_candidates(org_id, facility_id, date, start_time_str):
        """Tier 1 — employees with an explicit EmployeeServiceMapping for this facility."""
        employees = list(
            OrganizationEmployee.objects.filter(
                organization_id=org_id,
                status='ACTIVE',
                service_mappings__facility_id=facility_id,
                service_mappings__is_active=True,
            ).distinct()
        )

        available = [
            emp for emp in employees
            if start_time_str in AvailabilityService.get_available_slots(
                str(emp.auth_user_id), facility_id, date
            )
        ]
        return SmartAssignmentService._score_candidates(available, facility_id, date)

    @staticmethod
    def _get_capability_candidates(org_id, capability_key, facility_id, date, start_time_str):
        """
        Tier 2 — employees whose assigned ProviderRole has the required capability key.
        This is the core of role-based smart assignment.
        """
        from ..models import ProviderRoleCapability

        # Find all roles in this org that have the required capability
        role_ids = list(
            ProviderRoleCapability.objects.filter(
                capability_key=capability_key,
                provider_role__provider_id=org_id,          # scope to this org
            ).values_list('provider_role_id', flat=True)
        )

        if not role_ids:
            logger.info(f"[SmartAssign] Tier 2: No roles found with capability={capability_key}")
            return []

        employees = list(
            OrganizationEmployee.objects.filter(
                organization_id=org_id,
                status='ACTIVE',
                provider_role_id__in=role_ids,
            ).distinct()
        )

        logger.info(f"[SmartAssign] Tier 2: Found {len(employees)} employee(s) with capability={capability_key}")

        available = [
            emp for emp in employees
            if start_time_str in AvailabilityService.get_available_slots(
                str(emp.auth_user_id), facility_id, date
            )
        ]
        return SmartAssignmentService._score_candidates(available, facility_id, date)

    @staticmethod
    def _get_all_active_candidates(org_id, facility_id, date, start_time_str):
        """Tier 3 — all active employees in the org as a last resort."""
        employees = list(
            OrganizationEmployee.objects.filter(
                organization_id=org_id,
                status='ACTIVE',
            )
        )

        logger.info(f"[SmartAssign] Tier 3: Checking all {len(employees)} active employees.")

        available = [
            emp for emp in employees
            if start_time_str in AvailabilityService.get_available_slots(
                str(emp.auth_user_id), facility_id, date
            )
        ]
        return SmartAssignmentService._score_candidates(available, facility_id, date)
