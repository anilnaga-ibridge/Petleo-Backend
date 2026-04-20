from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime, timedelta, time
import requests
import logging
from .models import ServiceProvider, ProviderAvailability, EmployeeAvailability, OrganizationEmployee
from provider_dynamic_fields.models import ProviderTemplateFacility
from .services.availability_service import AvailabilityService
from .services.organization_availability_service import OrganizationAvailabilityService
from .services.smart_assignment_service import SmartAssignmentService
from .services.cached_slots import AvailabilityCacheService
from .models import OrganizationAvailability, AvailabilityMetric
from .models_scheduling import EmployeeWeeklySchedule, EmployeeLeave, EmployeeBlockTime, EmployeeDailySchedule
from .serializers_scheduling import (
    EmployeeWeeklyScheduleSerializer, 
    EmployeeDailyScheduleSerializer,
    EmployeeLeaveSerializer, 
    EmployeeBlockTimeSerializer
)

logger = logging.getLogger(__name__)

class AvailabilityViewSet(viewsets.ViewSet):
    """
    Handle slot generation and employee assignment logic.
    """
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'], url_path='(?P<provider_id>[^/.]+)/available-slots')
    def available_slots(self, request, provider_id=None):
        date_str = request.query_params.get('date')
        facility_id = request.query_params.get('facility_id')
        service_id = request.query_params.get('service_id')
        consultation_type_id = request.query_params.get('consultation_type_id')

        if not date_str:
            return Response({"error": "date is required (YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

        # Flexible lookup: Try PK first, then auth_user_id
        try:
            from django.core.exceptions import ValidationError
            provider = ServiceProvider.objects.get(id=provider_id)
        except (ServiceProvider.DoesNotExist, ValidationError, ValueError):
            provider = get_object_or_404(ServiceProvider, verified_user__auth_user_id=provider_id)

        weekday = target_date.weekday()
        
        # 1. Resolve Specialist ID (Employee or Virtual)
        employee_id = request.query_params.get('employee_id')
        if employee_id and employee_id.startswith('ind-'):
            employee_id = employee_id.replace('ind-', '')
        
        slots = []
        if provider.provider_type == 'INDIVIDUAL':
            # Use ServiceProvider's own availability (Solo mode)
            availabilities = provider.individual_availability.filter(day_of_week=weekday, is_active=True)
            occupied_times = self._get_occupied_slots(provider.id, date_str)
            
            for avail in availabilities:
                current = datetime.combine(target_date, avail.start_time)
                end = datetime.combine(target_date, avail.end_time)
                
                while current + timedelta(minutes=avail.slot_duration_minutes) <= end:
                    time_str = current.strftime('%H:%M')
                    if time_str not in occupied_times:
                        slots.append({
                            "time": time_str,
                            "tier": 1,
                            "type": "INSTANT_CONFIRMED"
                        })
                    current += timedelta(minutes=avail.slot_duration_minutes)
                    
        elif provider.provider_type == 'ORGANIZATION':
            if employee_id:
                # Specific Employee Path
                raw_slots = AvailabilityService.get_available_slots(employee_id, facility_id, target_date, consultation_type_id)
                slots = [{"time": s, "tier": 1, "type": "INSTANT_CONFIRMED"} for s in raw_slots]
            elif facility_id:
                # Service-First Aggregated Path (Tier 1 & Tier 2)
                slots = OrganizationAvailabilityService.get_org_available_slots(provider_id, facility_id, target_date, consultation_type_id)
            else:
                # Fallback: merge slots across all active employees
                employees = provider.employees.filter(status='ACTIVE')
                temp_slots = set()
                for emp in employees:
                    emp_slots = AvailabilityService.get_available_slots(str(emp.auth_user_id), None, target_date)
                    temp_slots.update(emp_slots)
                slots = sorted([{"time": s, "tier": 1, "type": "INSTANT_CONFIRMED"} for s in temp_slots], key=lambda x: x['time'])


        return Response({"slots": slots})

    @action(detail=False, methods=['get'], url_path='active-hours')
    def active_hours(self, request):
        """Fetch current availability for the logged-in provider (Individual)"""
        if not hasattr(request.user, 'provider_profile'):
             return Response([])
             
        provider = request.user.provider_profile
        avail = ProviderAvailability.objects.filter(provider=provider, is_active=True)
        return Response([{
            "day": a.day_of_week,
            "start": a.start_time.strftime('%H:%M'),
            "end": a.end_time.strftime('%H:%M'),
            "slot_duration_minutes": a.slot_duration_minutes,
            "active": True
        } for a in avail])

    @action(detail=False, methods=['post'], url_path='save-settings')
    def save_settings(self, request):
        """Save overall provider type and individual availability"""
        provider_type = request.data.get('provider_type')
        availability_data = request.data.get('availability', [])
        
        if not hasattr(request.user, 'provider_profile'):
             return Response({"error": "Profile not found"}, status=404)
             
        provider = request.user.provider_profile
        
        with transaction.atomic():
            if provider_type:
                provider.provider_type = provider_type
                provider.save()
                
            # Update availability (Solo mode)
            if provider.provider_type == 'INDIVIDUAL':
                # Clear existing
                ProviderAvailability.objects.filter(provider=provider).delete()
                for h in availability_data:
                    ProviderAvailability.objects.create(
                        provider=provider,
                        day_of_week=h['day_of_week'],
                        start_time=h['start_time'],
                        end_time=h['end_time'],
                        slot_duration_minutes=h.get('slot_duration_minutes', 30)
                    )
        
        return Response({"message": "Settings saved successfully"})

    @action(detail=False, methods=['post'], url_path='auto-assign')
    def auto_assign(self, request):
       """Internal endpoint to trigger hybrid assignment (Rule 2)"""
       booking_id = request.data.get('booking_id')
       facility_id = request.data.get('facility_id')
       org_id = request.data.get('organization_id')
       date = request.data.get('date')
       time_str = request.data.get('time')
       pet_id = request.data.get('pet_id')
       
       if not all([booking_id, facility_id, org_id]):
           return Response({"error": "Missing params"}, status=400)
           
       # 1. Check Service Config (Rule 2-3)
       from .models import ServiceAssignmentConfig
       config = ServiceAssignmentConfig.objects.filter(facility_id=facility_id).first()
       
       # Default: Standard, Auto-Assign enabled
       is_high_risk = config.risk_level == 'HIGH' if config else False
       is_auto_enabled = config.auto_assign_enabled if config else True
       
       if is_auto_enabled and not is_high_risk:
           # TRIGGER AUTO ASSIGNMENT
           best_emp = SmartAssignmentService.assign_employee_for_slot(org_id, facility_id, date, time_str, pet_id)
           if best_emp:
               # NOTIFY CUSTOMER SERVICE TO CONFIRM
               try:
                   url = f"http://localhost:8005/api/pet-owner/bookings/bookings/{booking_id}/assign-staff/"
                   requests.post(url, json={"employee_id": str(best_emp.auth_user_id)}, timeout=2)
                   return Response({"status": "AUTO_ASSIGNED", "employee_id": str(best_emp.auth_user_id)})
               except Exception as e:
                   logger.error(f"Failed to sync auto-assignment back to customer service: {e}")
                   
       return Response({"status": "TRIAGE_REQUIRED", "reason": "High risk or auto-assign disabled"})

    @action(detail=False, methods=['post'], url_path='check-slas')
    def check_slas(self, request):
        """Background task entry point to flag SLA misses (Rule 5)"""
        # Fetch all SEARCHING_STAFF bookings across all providers
        try:
            url = "http://localhost:8005/api/pet-owner/bookings/bookings/internal_triage_queue/"
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return Response({"error": "Failed to fetch triage queue"}, status=500)
            
            bookings = resp.json()
            processed_count = 0
            
            from .services.availability_metric_service import AvailabilityMetricService
            from .models import ServiceAssignmentConfig
            
            for b in bookings:
                if b['status'] != 'SEARCHING_STAFF': continue
                
                # Fetch SLA for this facility
                # Fallback to 15m
                sla_mins = 15
                config = ServiceAssignmentConfig.objects.filter(facility_id=b.get('facility_id')).first()
                if config:
                    sla_mins = config.sla_minutes
                
                created_at = datetime.fromisoformat(b['created_at'].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > created_at + timedelta(minutes=sla_mins):
                    # SLA MISSED! Move to UNASSIGNED
                    try:
                        update_url = f"http://localhost:8005/api/pet-owner/bookings/bookings/{b['id']}/"
                        requests.patch(update_url, json={"status": "UNASSIGNED"}, timeout=2)
                        
                        AvailabilityMetricService.log_event(
                            org_id=b.get('organization_id'),
                            event_type='SLA_MISS',
                            booking_id=b['id']
                        )
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to flag SLA miss for booking {b['id']}: {e}")
            
            return Response({"processed": processed_count})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='employee-hours')
    def employee_hours(self, request):
        """Fetch working hours for a specific organization employee"""
        employee_id = request.query_params.get('employee_id')
        if not employee_id:
            return Response({"error": "employee_id is required"}, status=400)
            
        avail = EmployeeAvailability.objects.filter(employee__id=employee_id, is_active=True)
        return Response([{
            "day": a.day_of_week,
            "start": a.start_time.strftime('%H:%M'),
            "end": a.end_time.strftime('%H:%M'),
            "slot_duration_minutes": a.slot_duration_minutes,
            "active": True
        } for a in avail])

    @action(detail=False, methods=['post'], url_path='save-employee-hours')
    def save_employee_hours(self, request):
        """Save working hours for a specific organization employee"""
        employee_id = request.data.get('employee_id')
        availability_data = request.data.get('availability', [])
        
        if not employee_id:
            return Response({"error": "employee_id is required"}, status=400)
            
        employee = get_object_or_404(OrganizationEmployee, id=employee_id)
        
        with transaction.atomic():
            # Clear existing
            EmployeeAvailability.objects.filter(employee=employee).delete()
            for h in availability_data:
                EmployeeAvailability.objects.create(
                    employee=employee,
                    day_of_week=h['day_of_week'],
                    start_time=h['start_time'],
                    end_time=h['end_time'],
                    slot_duration_minutes=h.get('slot_duration_minutes', 30)
                )
            
            # Since working hours changed, we should probably clear some cache
            # For simplicity, we can clear the next 7 days for this employee
            today = datetime.now().date()
            for i in range(7):
                AvailabilityCacheService.invalidate_employee_day(str(employee.auth_user_id), today + timedelta(days=i))
                    
        return Response({"message": "Employee hours saved successfully"})

    def _get_occupied_slots(self, provider_id, date_str, employee_id=None):
        # Strip prefix if present (Virtual Identity unification)
        if employee_id and isinstance(employee_id, str) and employee_id.startswith('ind-'):
            employee_id = employee_id.replace('ind-', '')
            
        try:
            # internal endpoint in customer_service
            url = f"http://localhost:8005/api/pet-owner/bookings/bookings/internal_bookings/"
            params = {"provider_id": provider_id, "date": date_str}
            if employee_id:
                params["employee_id"] = employee_id
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch internal bookings: {e}")
        return []

    @action(detail=False, methods=['post'], url_path='(?P<provider_id>[^/.]+)/assign-employee')
    def assign_employee(self, request, provider_id=None):
        """
        Smart auto-assign the best available employee for a chosen time.
        Model 2: Service-First logic delegating to SmartAssignmentService.
        """
        selected_time_str = request.data.get('selected_time')
        facility_id = request.data.get('facility_id')
        
        if not selected_time_str:
            return Response({"error": "selected_time is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Standardize date and time strings for the service
        try:
            if 'T' in selected_time_str:
                dt = datetime.fromisoformat(selected_time_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(selected_time_str, '%Y-%m-%d %H:%M:%S')
            
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M')
        except Exception:
            return Response({"error": "invalid time format"}, status=status.HTTP_400_BAD_REQUEST)
            
        provider = get_object_or_404(ServiceProvider, id=provider_id)
        if provider.provider_type != 'ORGANIZATION':
            return Response({"employee_id": None})
            
        # Delegate to SmartAssignmentService
        employee = SmartAssignmentService.assign_employee_for_slot(provider_id, facility_id, date_str, time_str)
        
        if not employee:
            return Response({"error": "No available employees for this slot"}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({
            "employee_id": str(employee.auth_user_id),
            "employee_name": employee.full_name
        })

    @action(detail=False, methods=['get'], url_path='(?P<provider_id>[^/.]+)/smart-assignment')
    def smart_assignment(self, request, provider_id=None):
        """
        Model 2: Auto-assign the best employee for a selected slot.
        """
        facility_id = request.query_params.get('facility_id')
        date_str = request.query_params.get('date')
        start_time_str = request.query_params.get('start_time')

        if not facility_id or not date_str or not start_time_str:
            return Response({"error": "facility_id, date, and start_time are required"}, status=400)

        employee = SmartAssignmentService.assign_employee_for_slot(provider_id, facility_id, date_str, start_time_str)
        
        if not employee:
            return Response({"error": "No qualified employee available for this slot"}, status=404)
            
        return Response({
            "employee_id": str(employee.auth_user_id),
            "employee_name": employee.full_name,
            "employee_rating": employee.average_rating
        })


class ScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for employees to submit schedules and providers to manage/approve them.
    Now using date-specific EmployeeDailySchedule with reasons.
    """
    queryset = EmployeeDailySchedule.objects.all()
    serializer_class = EmployeeDailyScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # 1. If user is a provider (owner), they see all employee schedules in their organization
        if hasattr(user, 'provider_profile'):
            return self.queryset.filter(employee__organization=user.provider_profile)
            
        # 2. Otherwise, check if they are an employee and show only their own
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
            return self.queryset.filter(employee=emp)
        except OrganizationEmployee.DoesNotExist:
            pass
            
        return self.queryset.none()

    def perform_create(self, serializer):
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=self.request.user.auth_user_id)
            serializer.save(employee=emp, status='PENDING')
        except OrganizationEmployee.DoesNotExist:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError("Only employees can submit schedules.")

    @action(detail=False, methods=['post'], url_path='bulk-submit')
    def bulk_submit(self, request):
        """
        Employee submits availability for multiple specific dates in a single call.
        Each entry: {date, start_time, end_time, reason, off: boolean}
        """
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=request.user.auth_user_id)
        except OrganizationEmployee.DoesNotExist:
            return Response({"error": "Employee profile not found"}, status=404)

        schedule_data = request.data.get('schedule', [])
        if not schedule_data:
            return Response({"error": "schedule data is required"}, status=400)

        with transaction.atomic():
            # For each date provided, replace PENDING/REJECTED entries
            for entry in schedule_data:
                target_date = entry.get('date')
                if not target_date: continue

                # Clear ANY existing daily schedules for this date to prevent duplications
                # This includes APPROVED, PENDING, and REJECTED
                EmployeeDailySchedule.objects.filter(
                    employee=emp,
                    date=target_date
                ).delete()

                is_off = entry.get('off', False)
                
                if is_off:
                    # Day Off requests require manual approval
                    EmployeeDailySchedule.objects.create(
                        employee=emp,
                        date=target_date,
                        start_time=time(0,0),
                        end_time=time(0,0),
                        reason=entry.get('reason') or 'Day Off',
                        status='PENDING' 
                    )
                else:
                    # Normal working days also require manual approval (Fixed auto-approval issue)
                    EmployeeDailySchedule.objects.create(
                        employee=emp,
                        date=target_date,
                        start_time=entry['start_time'],
                        end_time=entry['end_time'],
                        reason=entry.get('reason') or 'Regular Shift',
                        status='PENDING'
                    )

        result = EmployeeDailySchedule.objects.filter(employee=emp).order_by('-date')
        return Response(EmployeeDailyScheduleSerializer(result, many=True).data, status=201)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """
        Provider/Authorized Employee sees all PENDING schedule submissions from their employees.
        """
        user = request.user
        organization = None
        
        # 1. Check if Org Owner
        if hasattr(user, 'provider_profile'):
            organization = user.provider_profile
        else:
            # 2. Check if Authorized Employee
            from service_provider.models import OrganizationEmployee
            try:
                emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
                perms = emp.get_final_permissions()
                if 'ROLE_MANAGEMENT' in perms or 'CLINIC_MANAGEMENT' in perms:
                    organization = emp.organization
            except OrganizationEmployee.DoesNotExist:
                pass

        if not organization:
            return Response({"error": "Only providers or authorized staff can access approvals"}, status=403)

        pending = EmployeeDailySchedule.objects.filter(
            employee__organization=organization,
            status='PENDING'
        ).select_related('employee').order_by('date', 'employee__full_name')

        return Response(EmployeeDailyScheduleSerializer(pending, many=True).data)

    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        schedule = self.get_object()
        user = request.user
        permitted = False
        
        if hasattr(user, 'provider_profile') and schedule.employee.organization == user.provider_profile:
            permitted = True
        else:
            from service_provider.models import OrganizationEmployee
            try:
                emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
                perms = emp.get_final_permissions()
                if ('ROLE_MANAGEMENT' in perms or 'CLINIC_MANAGEMENT' in perms) and schedule.employee.organization == emp.organization:
                    permitted = True
            except OrganizationEmployee.DoesNotExist:
                pass

        if not permitted:
            return Response({"error": "Permission denied"}, status=403)

        schedule.status = 'APPROVED'
        schedule.approved_by_auth_id = request.user.auth_user_id
        schedule.save()

        # Invalidate Cache (Atomic on Commit)
        transaction.on_commit(lambda: AvailabilityCacheService.invalidate_employee_day(
            str(schedule.employee.auth_user_id), 
            schedule.date
        ))

        return Response(EmployeeDailyScheduleSerializer(schedule).data)

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        schedule = self.get_object()
        user = request.user
        permitted = False
        
        if hasattr(user, 'provider_profile') and schedule.employee.organization == user.provider_profile:
            permitted = True
        else:
            from service_provider.models import OrganizationEmployee
            try:
                emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
                perms = emp.get_final_permissions()
                if ('ROLE_MANAGEMENT' in perms or 'CLINIC_MANAGEMENT' in perms) and schedule.employee.organization == emp.organization:
                    permitted = True
            except OrganizationEmployee.DoesNotExist:
                pass

        if not permitted:
            return Response({"error": "Permission denied"}, status=403)

        reason = request.data.get('rejection_reason', 'No reason provided')
        schedule.status = 'REJECTED'
        schedule.rejection_reason = reason
        schedule.save()
        return Response(EmployeeDailyScheduleSerializer(schedule).data)


class LeaveViewSet(viewsets.ModelViewSet):
    """
    Manage employee leaves.
    Employees can create PENDING leaves.
    Admins can APPROVE/REJECT them.
    """
    queryset = EmployeeLeave.objects.all()
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Admins see all org leaves, employees see their own
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
            if hasattr(user, 'provider_profile'): # Is Org Owner
                 return self.queryset.filter(employee__organization=user.provider_profile)
            return self.queryset.filter(employee=emp)
        except OrganizationEmployee.DoesNotExist:
            if hasattr(user, 'provider_profile'):
                 return self.queryset.filter(employee__organization=user.provider_profile)
        return self.queryset.none()

    def perform_create(self, serializer):
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=self.request.user.auth_user_id)
            # Default to PENDING
            serializer.save(employee=emp, status='PENDING')
        except OrganizationEmployee.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Only employees can mark leaves.")

    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        leave = self.get_object()
        # Permission check: must be org owner
        if not hasattr(request.user, 'provider_profile') or leave.employee.organization != request.user.provider_profile:
             return Response({"error": "Permission denied"}, status=403)
        
        leave.status = 'APPROVED'
        leave.approved_by_auth_id = request.user.auth_user_id
        leave.save()

        # Invalidate Cache (Atomic on Commit)
        transaction.on_commit(lambda: AvailabilityCacheService.invalidate_employee_day(
            str(leave.employee.auth_user_id), 
            leave.date
        ))

        return Response(EmployeeLeaveSerializer(leave).data)

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if not hasattr(request.user, 'provider_profile') or leave.employee.organization != request.user.provider_profile:
             return Response({"error": "Permission denied"}, status=403)
        
        leave.status = 'REJECTED'
        leave.approved_by_auth_id = request.user.auth_user_id
        leave.save()
        return Response(EmployeeLeaveSerializer(leave).data)

class BlockTimeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeBlockTime.objects.all()
    serializer_class = EmployeeBlockTimeSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Both employee and provider can block time
    def perform_create(self, serializer):
        # ... logic to resolve employee ...
        serializer.save()
