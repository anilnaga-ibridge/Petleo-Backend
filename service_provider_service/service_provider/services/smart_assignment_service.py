import logging
import requests
from django.db import transaction
from django.conf import settings
from .availability_service import AvailabilityService
from ..models import OrganizationEmployee, OrganizationAvailability

logger = logging.getLogger(__name__)

class SmartAssignmentService:
    @staticmethod
    @transaction.atomic
    def assign_employee_for_slot(org_id, facility_id, date, start_time_str, pet_id=None):
        """Standardized assignment entry point with Weighted Scoring (Rule 1)"""
        capability_key = SmartAssignmentService._resolve_capability_for_facility(facility_id)
        
        # 1. Gather Candidates (Tier 1 -> 2 -> 3)
        candidates = SmartAssignmentService._get_mapped_candidates(org_id, facility_id, date, start_time_str)
        
        if not candidates and capability_key:
            candidates = SmartAssignmentService._get_capability_candidates(org_id, capability_key, facility_id, date, start_time_str)
            
        if not candidates:
            candidates = SmartAssignmentService._get_all_active_candidates(org_id, facility_id, date, start_time_str)
            
        if not candidates:
            return None

        # 2. Get Score Weights from Org Config (Rule 1)
        # Default to 40/25/20/15
        weights = {
            'qualification': 0.40,
            'busyness': 0.25,
            'rating': 0.20,
            'continuity': 0.15
        }
        
        org_cfg = OrganizationAvailability.objects.filter(organization_id=org_id).first()
        if org_cfg:
            weights['qualification'] = org_cfg.weight_qualification
            weights['busyness'] = org_cfg.weight_busyness
            weights['rating'] = org_cfg.weight_rating
            weights['continuity'] = org_cfg.weight_continuity

        # 3. Fetct Pet History if pet_id provided (Rule 1)
        history_emp_ids = []
        if pet_id:
            try:
                # Internal call to customer_service
                url = f"http://localhost:8005/api/pet-owner/bookings/bookings/internal_pet_history/"
                resp = requests.get(url, params={"pet_id": pet_id}, timeout=2)
                if resp.status_code == 200:
                    history_emp_ids = resp.json()
            except Exception as e:
                logger.warning(f"Failed to fetch pet history for continuity scoring: {e}")

        # 4. Final Weighted Scoring
        scored_candidates = []
        for cand in candidates:
            emp = cand['employee']
            
            # Busyness Score (Inverse of minutes, normalized 0-1)
            # Max minutes in shift ~ 480 (8h). 
            busy_score = 1.0 - min(cand['total_minutes'] / 480, 1.0)
            
            # Rating Score (Normalized 0-1)
            rating_score = cand['rating'] / 5.0
            
            # Continuity Score (Binary 0 or 1)
            cont_score = 1.0 if str(emp.auth_user_id) in history_emp_ids else 0.0
            
            # Qualification Score (Tier based)
            # Tier 1 = 1.0, Tier 2 = 0.7, Tier 3 = 0.4
            qual_score = 1.0 if cand.get('tier') == 1 else (0.7 if cand.get('tier') == 2 else 0.4)
            
            final_score = (
                (qual_score * weights['qualification']) +
                (busy_score * weights['busyness']) +
                (rating_score * weights['rating']) +
                (cont_score * weights['continuity'])
            )
            
            scored_candidates.append({
                'employee': emp,
                'score': final_score
            })
            
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        return scored_candidates[0]['employee']

    @staticmethod
    def _resolve_capability_for_facility(facility_id):
        if not facility_id: return None
        try:
            from provider_dynamic_fields.models import ProviderTemplateFacility
            try:
                facility = ProviderTemplateFacility.objects.get(id=facility_id)
            except:
                facility = ProviderTemplateFacility.objects.get(super_admin_facility_id=str(facility_id))
            
            return facility.required_capability or (facility.category.category_key if facility.category else None)
        except:
            return None

    @staticmethod
    def _get_mapped_candidates(org_id, facility_id, date, start_time_str):
        employees = list(OrganizationEmployee.objects.filter(
            organization_id=org_id, status='ACTIVE', 
            service_mappings__facility_id=facility_id, service_mappings__is_active=True
        ).distinct())
        
        available = [e for e in employees if start_time_str in AvailabilityService.get_available_slots(str(e.auth_user_id), facility_id, date)]
        return [{'employee': e, 'total_minutes': SmartAssignmentService._get_busyness(e, date), 'rating': float(e.average_rating or 0), 'tier': 1} for e in available]

    @staticmethod
    def _get_capability_candidates(org_id, capability_key, facility_id, date, start_time_str):
        from ..models import ProviderRoleCapability
        role_ids = list(ProviderRoleCapability.objects.filter(permission_key__startswith=f"{capability_key}_", provider_role__provider_id=org_id).values_list('provider_role_id', flat=True))
        employees = list(OrganizationEmployee.objects.filter(organization_id=org_id, status='ACTIVE', provider_role_id__in=role_ids).distinct())
        
        available = [e for e in employees if start_time_str in AvailabilityService.get_available_slots(str(e.auth_user_id), facility_id, date)]
        return [{'employee': e, 'total_minutes': SmartAssignmentService._get_busyness(e, date), 'rating': float(e.average_rating or 0), 'tier': 2} for e in available]

    @staticmethod
    def _get_all_active_candidates(org_id, facility_id, date, start_time_str):
        employees = list(OrganizationEmployee.objects.filter(organization_id=org_id, status='ACTIVE'))
        available = [e for e in employees if start_time_str in AvailabilityService.get_available_slots(str(e.auth_user_id), facility_id, date)]
        return [{'employee': e, 'total_minutes': SmartAssignmentService._get_busyness(e, date), 'rating': float(e.average_rating or 0), 'tier': 3} for e in available]

    @staticmethod
    def _get_busyness(employee, date):
        bookings = AvailabilityService._get_confirmed_bookings(str(employee.auth_user_id), date)
        total = 0
        from datetime import datetime
        for b in bookings:
            try:
                d = (datetime.strptime(b['end'], '%H:%M') - datetime.strptime(b['start'], '%H:%M')).total_seconds() / 60
                total += max(0, d)
            except: total += 30
        return total
