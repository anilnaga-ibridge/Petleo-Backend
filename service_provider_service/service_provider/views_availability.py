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
        
        slots = []
        if provider.provider_type == 'INDIVIDUAL':
            availabilities = provider.individual_availability.filter(day_of_week=weekday, is_active=True)
            occupied_times = self._get_occupied_slots(provider_id, date_str)
            
            for avail in availabilities:
                current = datetime.combine(target_date, avail.start_time)
                end = datetime.combine(target_date, avail.end_time)
                
                while current + timedelta(minutes=avail.slot_duration_minutes) <= end:
                    time_str = current.strftime('%H:%M')
                    if time_str not in occupied_times:
                        slots.append(time_str)
                    current += timedelta(minutes=avail.slot_duration_minutes)
                    
        elif provider.provider_type == 'ORGANIZATION':
            employee_id = request.query_params.get('employee_id')
            
            if employee_id and facility_id:
                # Specific Employee Path (Model 1)
                slots = AvailabilityService.get_available_slots(employee_id, facility_id, target_date, consultation_type_id)
            elif facility_id:
                # Service-First Aggregated Path (Model 2)
                slots = OrganizationAvailabilityService.get_org_available_slots(provider_id, facility_id, target_date, consultation_type_id)
            else:
                # Fallback or generic view (legacy)
                employees = provider.employees.filter(status='ACTIVE')
                temp_slots = set()
                for emp in employees:
                    emp_slots = AvailabilityService.get_available_slots(str(emp.auth_user_id), facility_id, target_date)
                    temp_slots.update(emp_slots)
                slots = sorted(list(temp_slots))
            
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
                    
        return Response({"message": "Employee hours saved successfully"})

    def _get_occupied_slots(self, provider_id, date_str, employee_id=None):
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
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
            return self.queryset.filter(employee=emp)
        except OrganizationEmployee.DoesNotExist:
            if hasattr(user, 'provider_profile'):
                return self.queryset.filter(employee__organization=user.provider_profile)
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

                # Remove existing schedules for this date to allow overwriting/editing
                EmployeeDailySchedule.objects.filter(
                    employee=emp,
                    date=target_date
                ).delete()

                is_off = entry.get('off', False)
                
                if is_off:
                    # Day Off requests still require manual approval
                    EmployeeDailySchedule.objects.create(
                        employee=emp,
                        date=target_date,
                        start_time=time(0,0),
                        end_time=time(0,0),
                        reason=entry.get('reason') or 'Day Off',
                        status='PENDING' 
                    )
                else:
                    # Normal working days are auto-approved
                    EmployeeDailySchedule.objects.create(
                        employee=emp,
                        date=target_date,
                        start_time=entry['start_time'],
                        end_time=entry['end_time'],
                        reason=entry.get('reason') or 'Regular Shift',
                        status='APPROVED'
                    )

        result = EmployeeDailySchedule.objects.filter(employee=emp).order_by('-date')
        return Response(EmployeeDailyScheduleSerializer(result, many=True).data, status=201)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """
        Provider sees all PENDING schedule submissions from their employees.
        """
        if not hasattr(request.user, 'provider_profile'):
            return Response({"error": "Only providers can access approvals"}, status=403)

        pending = EmployeeDailySchedule.objects.filter(
            employee__organization=request.user.provider_profile,
            status='PENDING'
        ).select_related('employee').order_by('date', 'employee__full_name')

        return Response(EmployeeDailyScheduleSerializer(pending, many=True).data)

    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        schedule = self.get_object()
        if not hasattr(request.user, 'provider_profile'):
            return Response({"error": "Permission denied"}, status=403)
        if schedule.employee.organization != request.user.provider_profile:
            return Response({"error": "Permission denied"}, status=403)

        schedule.status = 'APPROVED'
        schedule.approved_by_auth_id = request.user.auth_user_id
        schedule.save()
        return Response(EmployeeDailyScheduleSerializer(schedule).data)

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        schedule = self.get_object()
        if not hasattr(request.user, 'provider_profile'):
            return Response({"error": "Permission denied"}, status=403)
        if schedule.employee.organization != request.user.provider_profile:
            return Response({"error": "Permission denied"}, status=403)

        reason = request.data.get('rejection_reason', 'No reason provided')
        schedule.status = 'REJECTED'
        schedule.rejection_reason = reason
        schedule.save()
        return Response(EmployeeDailyScheduleSerializer(schedule).data)


class LeaveViewSet(viewsets.ModelViewSet):
    queryset = EmployeeLeave.objects.all()
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=self.request.user.auth_user_id)
            serializer.save(employee=emp)
        except OrganizationEmployee.DoesNotExist:
            raise serializers.ValidationError("Only employees can mark leaves.")

class BlockTimeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeBlockTime.objects.all()
    serializer_class = EmployeeBlockTimeSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Both employee and provider can block time
    def perform_create(self, serializer):
        # ... logic to resolve employee ...
        serializer.save()
