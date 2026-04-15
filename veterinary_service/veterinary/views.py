def get_clinic_context(request):
    """
    Robustly resolve clinic_id from request.
    Priority:
    1. Token (JWT payload) - most secure
    2. X-Clinic-ID header - standard header approach
    3. clinic_id query param - frontend-friendly fallback
    """
    # 1. Try from user object (set by middleware from JWT)
    clinic_id = getattr(request.user, 'clinic_id', None)
    if clinic_id:
        return clinic_id
    
    # 2. Try from JWT token payload
    token = getattr(request, 'auth', None)
    if token:
        if isinstance(token, dict):
            clinic_id = token.get('clinic_id')
        elif hasattr(token, 'payload'):
            clinic_id = token.payload.get('clinic_id')
        elif hasattr(token, 'get'):
            clinic_id = token.get('clinic_id')
        if clinic_id:
            request.user.clinic_id = str(clinic_id)
            return str(clinic_id)

    # 2.5 Try from request body (for POST/PUT requests)
    if request.method in ['POST', 'PUT', 'PATCH']:
        # Handle both DRF Request and standard Django HttpRequest
        data = getattr(request, 'data', {})
        clinic_id = data.get('clinic_id')
        if clinic_id:
            request.user.clinic_id = str(clinic_id)
            return str(clinic_id)

    # 3. Try from header
    clinic_id = request.META.get('HTTP_X_CLINIC_ID')
    if clinic_id:
        request.user.clinic_id = clinic_id
        return clinic_id

    # 4. Try from query param (frontend fallback)
    clinic_id = request.query_params.get('clinic_id')
    if clinic_id:
        request.user.clinic_id = clinic_id
        return clinic_id
    
    return None

def get_auth_user_id(request):
    """
    Robustly resolve auth_user_id (UUID string) from request.
    In this system, request.user.username is usually the UUID from Auth Service.
    """
    if hasattr(request.auth, 'get') and request.auth:
        auth_uid = request.auth.get('user_id')
        if auth_uid: return str(auth_uid)
    
    # Fallback to username if it looks like a UUID
    username = getattr(request.user, 'username', '')
    if len(username) > 30: # Likely a UUID
        return username
        
    return str(request.user.id) if getattr(request.user, 'id', None) else None
import logging
from django.utils import timezone, dateparse
from django.db import transaction
logger = logging.getLogger('veterinary')
from datetime import timedelta, date
from rest_framework import viewsets, permissions, status, filters
import django_filters.rest_framework
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import (
    Clinic, PetOwner, Pet, Visit,
    DynamicFieldDefinition, DynamicFieldValue,
    FormDefinition, FormField, FormSubmission,
    LabTestTemplate, LabTestField, LabOrder, LabResult,
    MedicalAppointment, StaffClinicAssignment,
    LabTest, Medicine, MedicineReminder, MedicineReminderSchedule,
    Prescription, PrescriptionItem, PharmacyTransaction,
    VisitInvoice, InvoiceLineItem,
    Vaccination, Deworming, SystemVaccinationReminder, SystemDewormingReminder
)
from .serializers import (
    ClinicSerializer, PetOwnerSerializer, PetSerializer, VisitSerializer,
    DynamicFieldDefinitionSerializer, DynamicFieldValueSerializer,
    DynamicEntitySerializer,
    FormDefinitionSerializer, FormSubmissionSerializer, VisitDetailSerializer,
    LabTestTemplateSerializer, LabTestFieldSerializer, LabOrderSerializer, LabResultSerializer, PharmacyDispenseSerializer,
    MedicalAppointmentSerializer, StaffClinicAssignmentSerializer,
    LabTestSerializer, MedicineSerializer, MedicineBatchSerializer, PrescriptionSerializer,
    PharmacyTransactionSerializer, VisitInvoiceSerializer, InvoiceLineItemSerializer,
    MedicineReminderSerializer, MedicineReminderScheduleSerializer
)
from .services import (
    DynamicEntityService, WorkflowService, MetadataService, 
    LabService, PharmacyService, ReminderService, VisitQueueService,
    VisitTimelineService, ClinicAnalyticsService,
    VeterinaryAvailabilityService, VeterinaryAppointmentService,
    ClinicRegistrationService
)
from .kafka.producer import producer
from .permissions import (
    HasVeterinaryAccess, IsClinicStaffOfPet, VeterinaryCheckoutPermission, 
    require_capability, require_granular_capability, has_capability_access
)
from .utils.permissions import permission_required
from .monetization import feature_tier, PRO, ENTERPRISE

class ClinicViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Clinic.objects.none()
        
        # Robust Role Extraction
        role = getattr(user, 'role', None)
        if not role and hasattr(self.request.auth, 'get'):
             role = self.request.auth.get('role')
        role = str(role or '').upper()

        # DEBUG LOGGING (Temporary)
        try:
             with open("/tmp/clinic_list_debug.log", "a") as f:
                 f.write(f"GET_QUERYSET: UserID={user.id} Type={type(user.id)} Role={role}\n")
        except: pass

        # Organizations see all their clinics
        if role in ['ORGANIZATION', 'INDIVIDUAL']:
            # Use Token User ID, not local user.id (which might be int 1)
            user_id = user.id
            if hasattr(self.request.auth, 'get'):
                 user_id = self.request.auth.get('user_id') or user.id
            return Clinic.objects.filter(organization_id=str(user_id))
        
        # Staff see clinics they are assigned to
        # [FIX] Use the same ID extraction logic as above (or user.username if that stores UUID)
        staff_user_id = user.id
        if hasattr(self.request.auth, 'get'):
             staff_user_id = self.request.auth.get('user_id') or staff_user_id
             
        return Clinic.objects.filter(staff_assignments__staff__auth_user_id=str(staff_user_id), staff_assignments__is_active=True)

    def perform_create(self, serializer):
        """
        ARCHITECTURAL LOCK-IN:
        1. Clinics are strictly OWNED by Organizations.
        2. Super Admins and Individual Providers cannot manually create additional clinics.
        3. The first clinic is auto-marked as primary for the 1:N scale.
        """
        user = self.request.user
        # DRF Authentication re-creates the user object, losing middleware attributes.
        # We must re-extract 'role' from the verified JWT token (request.auth).
        
        role = getattr(user, 'role', None)
        if not role:
            # request.auth is typically the AccessToken object
            auth_payload = self.request.auth
            if auth_payload and hasattr(auth_payload, 'get'):
                role = auth_payload.get('role')
        
        role = str(role or '').upper()
        
        # 1. Enforce Role: Organizations and Individuals can explicitly create clinics
        if role not in ['ORGANIZATION', 'INDIVIDUAL', 'ORGANIZATION_PROVIDER', 'PROVIDER']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(f"Only Organization or Individual Providers can explicitly create clinics. Your role: {role}")

        org_id = str(user.id)
        if hasattr(self.request.auth, 'get'):
             org_id = self.request.auth.get('user_id') or org_id
        
        # 2. Check for existing clinics to determine primary status
        # If no clinics exist for this org, this one is primary
        has_clinics = Clinic.objects.filter(organization_id=org_id).exists()
        
        instance = serializer.save(
            organization_id=org_id,
            is_primary=not has_clinics
        )
        
        # 3. Post-Creation Setup (Subscription, Roles etc)
        ClinicRegistrationService.initialize_new_clinic(instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        org_id = instance.organization_id
        
        # 1. Block deletion if it's the only clinic
        remaining_count = Clinic.objects.filter(organization_id=org_id).count()
        if remaining_count <= 1:
            return Response(
                {"error": "You must have at least one clinic. Deletion blocked."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. If deleting the primary, promote the next one
        if instance.is_primary:
            next_primary = Clinic.objects.filter(organization_id=org_id).exclude(id=instance.id).first()
            if next_primary:
                next_primary.is_primary = True
                next_primary.save()

        return super().destroy(request, *args, **kwargs)

class PetOwnerViewSet(viewsets.ModelViewSet):
    serializer_class = PetOwnerSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess, require_granular_capability('PATIENTS')]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'phone']
    filterset_fields = ['phone']

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return PetOwner.objects.filter(clinic_id=clinic_id)
        return PetOwner.objects.none()

    def list(self, request, *args, **kwargs):
        """
        Override list to auto-delete orphaned PetOwner records.
        Any record with auth_user_id=None whose phone doesn't exist in Auth Service is deleted before returning.
        """
        queryset = self.get_queryset()
        
        # Identify candidate orphaned records (no auth link, no email, placeholder name)
        unsynced = queryset.filter(auth_user_id__isnull=True)
        
        if unsynced.exists():
            from .auth_integration import AuthIntegrationService
            deleted_ids = []

            for owner_rec in unsynced:
                if not owner_rec.phone:
                    continue  # skip if no phone at all
                
                # Check if user exists in Auth Service
                auth_user = AuthIntegrationService.verify_user_exists(phone_number=owner_rec.phone)
                
                if auth_user is None:
                    # Confirmed: user does NOT exist in Auth Service — safe to delete
                    try:
                        from django.db import ProgrammingError
                        owner_rec.delete()
                        logger.info(
                            f"Auto-deleted orphaned PetOwner {owner_rec.id} "
                            f"(phone={owner_rec.phone}) — no matching Auth user found."
                        )
                    except Exception as del_err:
                        logger.warning(
                            f"Could not auto-delete orphaned PetOwner {owner_rec.id}: {del_err}. "
                            "Consider running migrations: python manage.py migrate"
                        )
                elif isinstance(auth_user, dict) and auth_user.get('auth_user_id'):
                    # User found in Auth Service — sync back their ID and name
                    owner_rec.auth_user_id = auth_user.get('auth_user_id')
                    if auth_user.get('full_name'):
                        owner_rec.name = auth_user.get('full_name')
                    if auth_user.get('email'):
                        owner_rec.email = auth_user.get('email')
                    owner_rec.save()
                    logger.info(
                        f"Re-linked PetOwner {owner_rec.id} to Auth user {owner_rec.auth_user_id}"
                    )
                # else: Auth Service returned True (unreachable / error) — skip deletion for safety

        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No active clinic context found. Please select a clinic.")
        
        # NEW: Register in Auth Service
        from .auth_integration import AuthIntegrationService
        auth_user_id = AuthIntegrationService.register_customer(
            full_name=self.request.data.get('name'),
            phone_number=self.request.data.get('phone'),
            email=self.request.data.get('email')
        )
        
        serializer.save(
            clinic_id=clinic_id,
            auth_user_id=auth_user_id,
            created_by=get_auth_user_id(self.request)
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        
        # NEW: Sync Update to Auth Service
        if instance.auth_user_id:
            from .auth_integration import AuthIntegrationService
            AuthIntegrationService.update_customer(
                instance.auth_user_id,
                {
                    'name': instance.name,
                    'phone': instance.phone,
                    'email': instance.email
                }
            )

class PetViewSet(viewsets.ModelViewSet):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess, require_granular_capability('PATIENTS')]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['owner']
    search_fields = ['name']

    search_fields = ['name']

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return Pet.objects.filter(owner__clinic_id=clinic_id)
        return Pet.objects.none()

    @action(detail=False, methods=['get'])
    def today(self, request):
        """
        Fetch pets registered today in the current clinic.
        Used for 'Pending Admissions' on the schedule sidebar.
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
            return Response([])
        
        from django.utils import timezone
        today = timezone.now().date()
        
        queryset = Pet.objects.filter(
            owner__clinic_id=clinic_id,
            created_at__date=today
        ).order_by('-created_at')
        
        return Response(PetSerializer(queryset, many=True, context={'request': request}).data)

    def _log_trace(self, msg):
        log_file = "/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service/middleware_trace.log"
        try:
            from django.utils import timezone
            from django.conf import settings
            with open(log_file, "a") as f:
                f.write(f"{timezone.now()} - [PET_TRACE] {msg}\n")
        except:
            pass

    def perform_create(self, serializer):
        try:
            self._log_trace(f"--- PET CREATE ATTEMPT ---")
            self._log_trace(f"RAW DATA: {self.request.data}")
            self._log_trace(f"VALIDATED DATA: {serializer.validated_data}")

            from rest_framework.exceptions import ValidationError
            
            # Support offline creation by receptionist
            owner_id = self.request.data.get('owner')
            
            if not owner_id:
                owner_name = self.request.data.get('owner_name')
                owner_phone = self.request.data.get('owner_phone')
                owner_email = self.request.data.get('owner_email')
                owner_address = self.request.data.get('owner_address') or self.request.data.get('address')
                owner_auth_id = self.request.data.get('owner_auth_id') or self.request.data.get('auth_user_id')
                clinic_id = get_clinic_context(self.request)
                
                self._log_trace(f"Owner ID missing. name: {owner_name}, phone: {owner_phone}, auth_id: {owner_auth_id}")

                if not clinic_id:
                    self._log_trace("ERROR: No active clinic context found.")
                    raise ValidationError({"error": "No active clinic context found."})
                    
                if owner_phone:
                    auth_user_id = owner_auth_id
                    
                    # Only register if we don't have an auth_user_id yet
                    if not auth_user_id:
                        self._log_trace(f"No auth_user_id provided. Attempting registration for {owner_phone}")
                        from .auth_integration import AuthIntegrationService
                        auth_user_id = AuthIntegrationService.register_customer(
                            full_name=owner_name or "New Owner",
                            phone_number=owner_phone,
                            email=owner_email
                        )

                    owner, created = PetOwner.objects.get_or_create(
                        clinic_id=clinic_id,
                        phone=owner_phone,
                        defaults={
                            'name': owner_name or "New Owner",
                            'email': owner_email,
                            'address': owner_address,
                            'auth_user_id': auth_user_id
                        }
                    )
                    
                    if not created:
                        updated = False
                        if auth_user_id and not owner.auth_user_id:
                            owner.auth_user_id = auth_user_id
                            updated = True
                        if owner_name and owner.name == "New Owner":
                            owner.name = owner_name
                            updated = True
                        if owner_email and not owner.email:
                            owner.email = owner_email
                            updated = True
                        if updated:
                            owner.save()

                    self._log_trace(f"SAVING WITH OWNER: {owner.id} (Created: {created}, AuthID: {auth_user_id})")
                    serializer.save(owner=owner, created_by=get_auth_user_id(self.request))
                    return
                else:
                    self._log_trace("ERROR: owner_phone missing in payload.")
                    raise ValidationError({"owner_phone": "Owner phone is required for registration."})

            self._log_trace(f"SAVING WITH PROVIDED OWNER_ID: {owner_id}")
            serializer.save(created_by=get_auth_user_id(self.request))
            self._log_trace("SAVE SUCCESSFUL")
        except Exception as e:
            self._log_trace(f"CRITICAL ERROR IN PET CREATE: {str(e)}")
            import traceback
            self._log_trace(traceback.format_exc())
            raise e

    def perform_update(self, serializer):
        """
        Handle Patient updates.
        Senior Developer Rule: For Owners, we allow updating owner_name/phone indirectly 
        through the Pet registration/edit flow.
        """
        try:
            self._log_trace(f"PET UPDATE START: Request data: {self.request.data}")
            owner_name = self.request.data.get('owner_name')
            owner_phone = self.request.data.get('owner_phone')
            owner_email = self.request.data.get('owner_email')
            owner_address = self.request.data.get('owner_address') or self.request.data.get('address')
            pet = self.get_object()
            
            if owner_phone and pet.owner:
                # Update owner info if changed
                owner = pet.owner
                needs_save = False
                if owner_name and owner.name != owner_name:
                    owner.name = owner_name
                    needs_save = True
                if owner_phone and owner.phone != owner_phone:
                    owner.phone = owner_phone
                    needs_save = True
                if owner_email and owner.email != owner_email:
                    owner.email = owner_email
                    needs_save = True
                if owner_address and owner.address != owner_address:
                    owner.address = owner_address
                    needs_save = True
                
                if needs_save:
                    owner.save()
                    self._log_trace(f"Updated Owner Info: {owner.id}")
            
            serializer.save()
            self._log_trace("UPDATE SUCCESSFUL")
        except Exception as e:
            self._log_trace(f"ERROR IN PET UPDATE: {str(e)}")
            raise e

    @action(detail=True, methods=["patch"], url_path="clinic-update", permission_classes=[permissions.IsAuthenticated, IsClinicStaffOfPet])
    def clinic_update(self, request, pk=None):
        """
        Specialized update for clinics to modify limited fields.
        """
        pet = self.get_object()
        allowed_fields = ["weight", "notes", "tag", "color", "is_active"]
        
        # Filter data to only include allowed fields
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        from .permissions import log
        log(f"PetViewSet.clinic_update: Request Data: {request.data}")
        log(f"PetViewSet.clinic_update: Filtered Data: {update_data}")

        serializer = self.get_serializer(pet, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        log(f"PetViewSet.clinic_update: Validated Data: {serializer.validated_data}")
        serializer.save()
        log("PetViewSet.clinic_update: Save Successful")
        
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def dynamic_data(self, request, pk=None):
        """
        Save dynamic data for a Pet.
        Body: {"key": "value", ...}
        """
        pet = self.get_object()
        try:
            DynamicEntityService.save_entity_data(
                pet.owner.clinic.id, 
                pet.id, 
                'PET', 
                request.data
            )
            return Response({'status': 'success'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        GET /api/veterinary/pets/{id}/history/
        Returns visit and vitals history for the pet.
        """
        pet = self.get_object()
        visits = Visit.objects.filter(pet=pet).order_by('-created_at')
        
        history_data = []
        for visit in visits:
            summary = MetadataService.get_visit_summary(visit.id)
            history_data.append({
                "id": str(visit.id),
                "date": visit.created_at,
                "status": visit.status,
                "reason": visit.reason,
                "vitals": summary.get("vitals", {}),
                "doctor": summary.get("doctor_assigned", "TBD"),
                "prescription_count": len(summary.get("prescription", {}).get("medicines", [])) if summary.get("prescription") else 0
            })
            
        return Response(history_data)

class VisitQueueViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'], url_path='(?P<queue_name>[^/.]+)')
    def get_queue(self, request, queue_name=None):
        """
        GET /veterinary/visits/queues/{queue_name}
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response([], status=status.HTTP_200_OK)
             
        # Map queue name to required capability
        REQUIRED_CAPS = {
            'WAITING_ROOM': 'VISITS',
            'VITALS_QUEUE': 'VETERINARY_ASSISTANT',
            'DOCTOR_QUEUE': 'DOCTOR_STATION',
            'LAB_QUEUE': 'LABS',
            'PHARMACY_QUEUE': 'PHARMACY'
        }
        
        required_cap = REQUIRED_CAPS.get(queue_name)
        
        if required_cap:
            if not has_capability_access(request.user, required_cap, 'view'):
                return Response({'error': f'Permission denied. Missing capability: {required_cap}'}, status=status.HTTP_403_FORBIDDEN)
        
        date_param = request.query_params.get('date')
        queryset = VisitQueueService.get_queue(queue_name, clinic_id, date_param)
        return Response(VisitSerializer(queryset, many=True).data)

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'])
    @feature_tier(PRO)
    def dashboard(self, request):
        """
        GET /veterinary/analytics/dashboard?date=YYYY-MM-DD&service_id=UUID
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response({})
             
        date_param = request.query_params.get('date')
        service_id = request.query_params.get('service_id')
        metrics = ClinicAnalyticsService.get_dashboard_metrics(clinic_id, date_param, service_id=service_id)
        return Response(metrics)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        GET /veterinary/analytics/summary
        Real-time operational summary (Total, Status Counts, Queue).
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response({})
              
        user_id = get_auth_user_id(request)
        date_param = request.query_params.get('date')
        data = ClinicAnalyticsService.get_live_summary(clinic_id, user_id=user_id, date_param=date_param)
        return Response(data)

class VisitViewSet(viewsets.ModelViewSet):
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        
        if clinic_id:
            return Visit.objects.filter(clinic_id=clinic_id)
        return Visit.objects.none()

    def perform_create(self, serializer):
        # [SENIOR DEV FIX] STRICT: Always use clinic from context, never trust frontend payload
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No active clinic context found. Please select a clinic.")
            
        # Duplicate Protection: Block creating a new visit today if an active one exists
        pet_id = serializer.validated_data.get('pet')
        if pet_id:
            from django.utils import timezone
            today = timezone.now().date()
            active_exists = Visit.objects.filter(
                clinic_id=clinic_id,
                pet=pet_id,
                created_at__date=today
            ).exclude(status='CLOSED').exists()
            
            if active_exists:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"non_field_errors": ["An active visit already exists for this patient today."]})

        instance = serializer.save(
            clinic_id=clinic_id, 
            created_by=get_auth_user_id(self.request)
        )

        producer.send_event('VET_VISIT_CREATED', {
            'visit_id': str(instance.id),
            'pet_id': str(instance.pet.id),
            'clinic_id': str(instance.clinic.id),
            'status': instance.status
        })

        from .models import VeterinaryAuditLog
        VeterinaryAuditLog.objects.create(
            visit=instance,
            action_type='VISIT_CREATED',
            performed_by=str(self.request.user.id)
        )

    def perform_update(self, serializer):
        # [SENIOR DEV FIX] Handle status transitions via standard update/patch
        visit = self.get_object()
        old_status = visit.status
        new_status = serializer.validated_data.get('status')

        if new_status and new_status != old_status:
            try:
                # Use WorkflowService to handle validation and side effects (timestamps, etc.)
                WorkflowService.transition_visit(visit, new_status, user_role=get_auth_user_id(self.request))
                # Remove status from validated_data so serializer doesn't re-save it
                serializer.validated_data.pop('status')
            except ValueError as e:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"status": str(e)})

        serializer.save()

    @action(detail=True, methods=['post'], url_path='check-in')
    @permission_required('veterinary.visits', 'edit')
    def check_in(self, request, pk=None):
        visit = self.get_object()

        # 1. Enforce doctor assignment
        doctor_auth_id = request.data.get('assigned_doctor_auth_id') or visit.assigned_doctor_auth_id
        if not doctor_auth_id:
            return Response({'error': 'Doctor assignment is mandatory for check-in.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Update doctor if new ID provided in request
            if request.data.get('assigned_doctor_auth_id') and (request.data.get('assigned_doctor_auth_id') != visit.assigned_doctor_auth_id):
                visit.assigned_doctor_auth_id = request.data.get('assigned_doctor_auth_id')
                visit.save(update_fields=['assigned_doctor_auth_id'])
                
            WorkflowService.transition_visit(visit, 'CHECKED_IN', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """
        Generic status transition endpoint.
        Body: { "status": "NEW_STATUS" }
        """
        visit = self.get_object()
        new_status = request.data.get('status')
        if not new_status:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            WorkflowService.transition_visit(visit, new_status, user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='record-vitals')
    @permission_required('veterinary.vitals', 'create')
    def record_vitals(self, request, pk=None):
        visit = self.get_object()
        try:
            # 1. Save data
            DynamicEntityService.save_entity_data(
                visit.clinic.id, 
                visit.id, 
                'VITALS', 
                request.data
            )
            # 2. Transition
            WorkflowService.transition_visit(visit, 'VITALS_RECORDED', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='assign-doctor')
    @permission_required('veterinary.visits', 'edit')
    def assign_doctor(self, request, pk=None):
        visit = self.get_object()
        doctor_id = request.data.get('doctor_id')
        if not doctor_id:
             return Response({'error': 'doctor_id is required'}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            visit.assigned_doctor_auth_id = doctor_id
            visit.save(update_fields=['assigned_doctor_auth_id'])
            WorkflowService.transition_visit(visit, 'DOCTOR_ASSIGNED', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status, 'assigned_doctor_auth_id': doctor_id})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='complete-consultation')
    def complete_consultation(self, request, pk=None):
        visit = self.get_object()
        try:
            WorkflowService.transition_visit(visit, 'CONSULTATION_DONE', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='finalize-prescription')
    def finalize_prescription(self, request, pk=None):
        visit = self.get_object()
        try:
            WorkflowService.transition_visit(visit, 'PRESCRIPTION_FINALIZED', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """
        Consolidated finalize endpoint for consultation.
        Handles prescriptions, lab orders, vaccinations, deworming, and transition.
        """
        visit = self.get_object()
        data = request.data
        user_auth_id = get_auth_user_id(request)
        
        try:
            with transaction.atomic():
                # 1. Update Consultation Notes
                notes = data.get('consultation_notes')
                if notes:
                    visit.consultation_notes = notes
                    visit.save(update_fields=['consultation_notes'])

                # 2. Handle Prescription
                prescription_data = data.get('prescription')
                if prescription_data and prescription_data.get('medicines'):
                    MetadataService.submit_form(
                        visit.id,
                        'PRESCRIPTION',
                        prescription_data,
                        user_auth_id
                    )

                # 3. Handle Lab Order
                lab_data = data.get('lab_order')
                if lab_data and lab_data.get('tests'):
                    MetadataService.submit_form(
                        visit.id,
                        'LAB_ORDER',
                        lab_data,
                        user_auth_id
                    )

                # 4. Handle Vaccinations
                vaccinations_data = data.get('vaccinations', [])
                for v in vaccinations_data:
                    vaccine_name = v.get('vaccine_name')
                    if vaccine_name:
                        date_given = v.get('date_given')
                        if isinstance(date_given, str):
                            date_given = dateparse.parse_date(date_given)
                        if not date_given:
                            date_given = timezone.now().date()

                        next_due = v.get('next_due_date')
                        if isinstance(next_due, str):
                            next_due = dateparse.parse_date(next_due)
                        if not next_due:
                            next_due = (timezone.now() + timedelta(days=365)).date()
                            
                        vaccination = Vaccination.objects.create(
                            pet=visit.pet,
                            vaccine_name=vaccine_name,
                            date_given=date_given,
                            next_due_date=next_due,
                            notes=v.get('notes'),
                            doctor_id=user_auth_id
                        )
                        # Auto-generate reminders
                        if vaccination.next_due_date:
                            next_due_date = vaccination.next_due_date
                            SystemVaccinationReminder.objects.create(
                                pet=vaccination.pet,
                                pet_owner_id=vaccination.pet.owner.auth_user_id or "UNKNOWN",
                                vaccine_name=vaccination.vaccine_name,
                                next_due_date=next_due_date,
                                reminder_date=next_due_date - timedelta(days=7),
                                status='PENDING'
                            )
                            SystemVaccinationReminder.objects.create(
                                pet=vaccination.pet,
                                pet_owner_id=vaccination.pet.owner.auth_user_id or "UNKNOWN",
                                vaccine_name=vaccination.vaccine_name,
                                next_due_date=next_due_date,
                                reminder_date=next_due_date - timedelta(days=1),
                                status='PENDING'
                            )

                # 5. Handle Deworming
                deworming_data = data.get('deworming')
                if deworming_data and deworming_data.get('medicine_name'):
                    date_given = deworming_data.get('date_given')
                    if isinstance(date_given, str):
                        date_given = dateparse.parse_date(date_given)
                    if not date_given:
                        date_given = timezone.now().date()

                    next_due = deworming_data.get('next_due_date')
                    if isinstance(next_due, str):
                        next_due = dateparse.parse_date(next_due)
                    if not next_due:
                        next_due = (timezone.now() + timedelta(days=90)).date() # Default 90 days for deworming

                    deworming = Deworming.objects.create(
                        pet=visit.pet,
                        medicine_name=deworming_data.get('medicine_name'),
                        date_given=date_given,
                        next_due_date=next_due,
                        doctor_id=user_auth_id
                    )
                    # Auto-generate reminders
                    if deworming.next_due_date:
                        next_due_date = deworming.next_due_date
                        SystemDewormingReminder.objects.create(
                            pet=deworming.pet,
                            pet_owner_id=deworming.pet.owner.auth_user_id or "UNKNOWN",
                            medicine_name=deworming.medicine_name,
                            next_due_date=next_due_date,
                            reminder_date=next_due_date - timedelta(days=7),
                            status='PENDING'
                        )
                        SystemDewormingReminder.objects.create(
                            pet=deworming.pet,
                            pet_owner_id=deworming.pet.owner.auth_user_id or "UNKNOWN",
                            medicine_name=deworming.medicine_name,
                            next_due_date=next_due_date,
                            reminder_date=next_due_date - timedelta(days=1),
                            status='PENDING'
                        )

                # 6. Final Status Transition
                next_status = data.get('next_status')
                if next_status:
                    WorkflowService.transition_visit(visit, next_status, user_role=user_auth_id)
                
                # NEW: Trigger Kafka Event for Final Visit Summary
                producer.send_event('VET_VISIT_SUMMARY_PUBLISHED', {
                    'visit_id': str(visit.id),
                    'pet_id': str(visit.pet.id),
                    'pet_external_id': getattr(visit.pet, 'external_id', None),
                    'owner_auth_id': getattr(visit.pet.owner, 'auth_user_id', None),
                    'clinic_name': visit.clinic.name,
                    'consultation_notes': visit.consultation_notes,
                    'finalized_at': timezone.now().isoformat()
                })

            return Response({'status': 'success', 'new_status': visit.status})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='close-visit')
    @permission_required('VETERINARY_CHECKOUT', 'edit')
    def close_visit(self, request, pk=None):
        visit = self.get_object()
        try:
            WorkflowService.transition_visit(visit, 'CLOSED', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='submit/(?P<form_code>[^/.]+)')
    def submit_form(self, request, pk=None, form_code=None):
        """
        Submit a form (Vitals, Prescription, etc.) for this visit.
        """
        visit = self.get_object()
        try:
            submission = MetadataService.submit_form(
                visit.id, 
                form_code, 
                request.data, 
                get_auth_user_id(request)
            )
            return Response(FormSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get full visit summary (Doctor View).
        """
        try:
            summary = MetadataService.get_visit_summary(pk)
            return Response(summary)
        except Visit.DoesNotExist:
            return Response({'error': 'Visit not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """
        Get visit timeline (SLA tracking).
        """
        try:
            timeline = VisitTimelineService.get_timeline(pk)
            return Response(timeline)
        except Visit.DoesNotExist:
            return Response({'error': 'Visit not found'}, status=status.HTTP_404_NOT_FOUND)

class PetOwnerClientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for Pet Owners to view their own data.
    """
    permission_classes = [permissions.IsAuthenticated] 

    def get_queryset(self):
        # Filter visits where the pet belongs to the logged-in user
        user_id = get_auth_user_id(self.request)
        return Visit.objects.filter(pet__owner__auth_user_id=user_id).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def pets(self, request):
        """
        GET /veterinary/pet-owner/pets
        """
        user_id = get_auth_user_id(request)
        pets = Pet.objects.filter(owner__auth_user_id=user_id)
        return Response(PetSerializer(pets, many=True).data)

    @action(detail=False, methods=['get'])
    def visits(self, request):
        """
        GET /veterinary/pet-owner/visits
        """
        visits = self.get_queryset()
        return Response(VisitSerializer(visits, many=True).data)

    @action(detail=False, methods=['get'], url_path='visit/(?P<visit_id>[^/.]+)')
    def visit_detail(self, request, visit_id=None):
        """
        GET /veterinary/pet-owner/visit/{id}
        """
        try:
            user_id = get_auth_user_id(request)
            visit = Visit.objects.get(id=visit_id, pet__owner__auth_user_id=user_id)
            return Response(VisitDetailSerializer(visit).data)
        except Visit.DoesNotExist:
            return Response({'error': 'Visit not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def invoices(self, request):
        """
        GET /veterinary/pet-owner/invoices
        """
        invoices = VisitInvoice.objects.filter(visit__pet__owner__auth_user_id=request.user.id)
        return Response(VisitInvoiceSerializer(invoices, many=True).data)

    @action(detail=False, methods=['post'], url_path='pay/(?P<invoice_id>[^/.]+)')
    def pay(self, request, invoice_id=None):
        """
        POST /veterinary/pet-owner/pay/{invoice_id}
        """
        try:
            invoice = VisitInvoice.objects.get(id=invoice_id, visit__pet__owner__auth_user_id=request.user.id)
            invoice.status = 'PAID'
            invoice.save()
            return Response({'status': 'Payment successful'})
        except VisitInvoice.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def labs(self, request):
        """
        GET /veterinary/pet-owner/labs
        """
        # Fetch lab results (FormSubmissions with code LAB_RESULT_FORM)
        submissions = FormSubmission.objects.filter(
            visit__pet__owner__auth_user_id=request.user.id,
            form_definition__code='LAB_RESULT_FORM'
        )
        return Response(FormSubmissionSerializer(submissions, many=True).data)

    @action(detail=False, methods=['get'])
    def prescriptions(self, request):
        """
        GET /veterinary/pet-owner/prescriptions
        """
        submissions = FormSubmission.objects.filter(
            visit__pet__owner__auth_user_id=request.user.id,
            form_definition__code='PRESCRIPTION'
        )
        return Response(FormSubmissionSerializer(submissions, many=True).data)

    @action(detail=False, methods=['get'])
    def appointments(self, request):
        """
        GET /veterinary/pet-owner/appointments
        """
        user_id = get_auth_user_id(request)
        appointments = MedicalAppointment.objects.filter(
            pet__owner__auth_user_id=user_id
        ).order_by('-appointment_date', '-start_time')
        
        from .serializers import MedicalAppointmentSerializer
        return Response(MedicalAppointmentSerializer(appointments, many=True).data)

    @action(detail=False, methods=['get'])
    def reminders(self, request):
        """
        GET /veterinary/pet-owner/reminders
        Returns all medicine reminders for this owner.
        """
        user_id = get_auth_user_id(request)
        reminders = MedicineReminder.objects.filter(pet_owner_auth_id=user_id)
        return Response(MedicineReminderSerializer(reminders, many=True).data)

    @action(detail=False, methods=['get'])
    def schedules(self, request):
        """
        GET /veterinary/pet-owner/schedules
        Returns all schedule entries for this owner. 
        Supports ?date=YYYY-MM-DD
        """
        user_id = get_auth_user_id(request)
        date_param = request.query_params.get('date')
        
        queryset = MedicineReminderSchedule.objects.filter(reminder__pet_owner_auth_id=user_id)
        
        if date_param:
            queryset = queryset.filter(scheduled_datetime__date=date_param)
            
        return Response(MedicineReminderScheduleSerializer(queryset, many=True).data)

class FormDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = FormDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]
    lookup_field = 'code'

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        from django.db.models import Q
        # Global forms (clinic=None) OR specifically for this clinic
        if clinic_id:
            return FormDefinition.objects.filter(Q(clinic_id=clinic_id) | Q(clinic__isnull=True))
        return FormDefinition.objects.filter(clinic__isnull=True)

    def perform_create(self, serializer):
        # [SENIOR DEV FIX] STRICT: Organizations cannot create global forms.
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("Clinic context required to create form definitions.")
        
        serializer.save(clinic_id=clinic_id)

# ========================
# PHASE 3: EXECUTION VIEWSETS
# ========================

class LabViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'], permission_classes=[require_granular_capability('LABS')])
    def pending(self, request):
        """
        List pending lab orders for the clinic.
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response([], status=status.HTTP_200_OK)
             
        orders = LabService.get_pending_lab_orders(clinic_id)
        return Response(orders)

class PharmacyViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'], permission_classes=[require_granular_capability('VETERINARY_PRESCRIPTIONS')])
    def pending(self, request):
        """
        List pending prescriptions.
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response([], status=status.HTTP_200_OK)
             
        prescriptions = PharmacyService.get_pending_prescriptions(clinic_id)
        return Response(PrescriptionSerializer(prescriptions, many=True).data)

    @action(detail=False, methods=['post'], permission_classes=[require_granular_capability('VETERINARY_PRESCRIPTIONS')])
    def dispense(self, request):
        """
        Dispense medicines for a prescription.
        Body: { "prescription_id": "UUID" }
        """
        prescription_id = request.data.get('prescription_id') or request.data.get('submission_id')
        if not prescription_id:
            return Response({'error': 'prescription_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response({'error': 'No clinic context found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Secure by ensuring prescription belongs to clinic
            prescription = Prescription.objects.get(id=prescription_id, visit__clinic_id=clinic_id)
            dispense = PharmacyService.dispense_medicines(prescription.id, get_auth_user_id(request))
            return Response(PharmacyDispenseSerializer(dispense).data)
        except Prescription.DoesNotExist:
            return Response({'error': 'Prescription not found in this clinic'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MedicineReminderViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineReminderSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            return MedicineReminder.objects.none()
        
        # Determine if we are on pet owner side or clinic staff side
        user_role = getattr(self.request.user, 'role', '').upper()
        if user_role == 'PET_OWNER':
            return MedicineReminder.objects.filter(pet__owner__auth_user_id=self.request.user.id)
        
        return MedicineReminder.objects.filter(pet__owner__clinic_id=clinic_id)

    def perform_create(self, serializer):
        serializer.save(created_by_auth_id=get_auth_user_id(self.request))

    @action(detail=False, methods=['get'])
    def today(self, request):
        """
        GET /api/veterinary/medicine-reminders/today
        Returns today's pending/actual doses for current user.
        """
        from django.utils import timezone
        today = timezone.now().date()
        user_id = get_auth_user_id(request)
        
        # Filter schedules for today belonging to this user's pets
        schedules = MedicineReminderSchedule.objects.filter(
            scheduled_datetime__date=today,
            reminder__pet_owner_auth_id=user_id
        ).select_related('reminder', 'reminder__medicine', 'reminder__pet')
        
        return Response(MedicineReminderScheduleSerializer(schedules, many=True).data)

class MedicineReminderScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineReminderScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_id = get_auth_user_id(self.request)
        return MedicineReminderSchedule.objects.filter(reminder__pet_owner_auth_id=user_id)

    @action(detail=True, methods=['post'])
    def taken(self, request, pk=None):
        """
        POST /api/veterinary/medicine-reminders/{id}/taken
        """
        from django.utils import timezone
        schedule = self.get_object()
        schedule.status = 'TAKEN'
        schedule.taken_at = timezone.now()
        schedule.save()
        return Response({'status': 'success'})

# Alias for backward compatibility if needed in URLs
ReminderViewSet = MedicineReminderViewSet

class LabTestTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing clinical lab templates (e.g. CBC, KFT).
    """
    serializer_class = LabTestTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        # In a real SaaS, we'd filter by clinic_id or show globals
        return LabTestTemplate.objects.filter(is_active=True)

class LabTestFieldViewSet(viewsets.ModelViewSet):
    serializer_class = LabTestFieldSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        return LabTestField.objects.all()

class DynamicFieldDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = DynamicFieldDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return DynamicFieldDefinition.objects.filter(clinic_id=clinic_id)
        return DynamicFieldDefinition.objects.none()

    def perform_create(self, serializer):
        # [SENIOR DEV FIX] Enforce clinic from context
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("Cloud context required to create field definitions.")
             
        serializer.save(clinic_id=clinic_id)

class DynamicEntityViewSet(viewsets.ViewSet):
    """
    Generic ViewSet for Virtual Entities (Prescriptions, Labs, etc.)
    """
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def create(self, request):
        serializer = DynamicEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        entity_type = serializer.validated_data['entity_type']
        data = serializer.validated_data['data']
        clinic_id = getattr(request.user, 'clinic_id', None)

        if not clinic_id:
             return Response({'error': 'No active clinic context found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Capability Check
            user_perms = getattr(request.user, 'permissions', [])
            required_cap = None
            if entity_type == 'VITALS': required_cap = 'VETERINARY_ASSISTANT'
            elif entity_type == 'PRESCRIPTION': required_cap = 'VETERINARY_PRESCRIPTIONS'
            elif entity_type == 'LAB': required_cap = 'LABS'
            
            if required_cap and required_cap not in user_perms:
                 return Response({'error': f'Missing capability: {required_cap}'}, status=status.HTTP_403_FORBIDDEN)

            entity_id = DynamicEntityService.create_virtual_entity(
                clinic_id, 
                entity_type, 
                data
            )
            
            # Emit generic event or specific based on type
            producer.send_event(f'{entity_type}_CREATED', {
                'entity_id': str(entity_id),
                'entity_type': entity_type
            })
            
            return Response({'id': entity_id, 'status': 'created'}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ========================
# PHASE 3.5: PROFESSIONAL LAB VIEWS
# ========================

class LabTestTemplateViewSet(viewsets.ModelViewSet):
    """
    Manage Lab Test Templates (CBC, LFT, etc.)
    """
    queryset = LabTestTemplate.objects.filter(is_active=True)
    serializer_class = LabTestTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

class LabOrderViewSet(viewsets.ModelViewSet):
    """
    Manage Lab Orders and Results.
    """
    queryset = LabOrder.objects.all()
    serializer_class = LabOrderSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return LabOrder.objects.filter(visit__clinic_id=clinic_id).order_by('-created_at')
        return LabOrder.objects.none()

    def perform_create(self, serializer):
        """
        Doctor creates a Lab Order.
        """
        visit = serializer.validated_data['visit']
        
        # 1. Update Visit Status
        from .services import WorkflowService
        try:
             WorkflowService.transition_visit(visit, 'LAB_REQUESTED')
        except ValueError:
             pass # Ignore if already in/past this state
             
        # 2. Save Order
        serializer.save(
            status='LAB_REQUESTED',
            requested_by=self.request.user.id
        )

    @action(detail=True, methods=['post'])
    def submit_results(self, request, pk=None):
        """
        Lab Tech submits results.
        Body: { "results": [ { "field_id": "UUID", "value": "12.5", "notes": "..." } ] }
        """
        order = self.get_object()
        results_data = request.data.get('results', [])
        
        if not results_data:
            return Response({'error': 'No results provided'}, status=status.HTTP_400_BAD_REQUEST)

        import datetime
        from django.utils import timezone
        
        saved_results = []
        try:
            from django.db import transaction
            with transaction.atomic():
                for res in results_data:
                    field_id = res.get('field_id')
                    value_str = str(res.get('value', ''))
                    
                    try:
                        field_def = LabTestField.objects.get(id=field_id, template=order.template)
                    except LabTestField.DoesNotExist:
                        continue 
                        
                    # Calculate Flag (LOW/HIGH/NORMAL)
                    flag = 'NORMAL'
                    try:
                        val_float = float(value_str)
                        if field_def.min_value is not None and val_float < field_def.min_value:
                            flag = 'LOW'
                        elif field_def.max_value is not None and val_float > field_def.max_value:
                            flag = 'HIGH'
                    except ValueError:
                        pass # Non-numeric result, flag remains NORMAL or None
                        
                    result_obj, _ = LabResult.objects.update_or_create(
                        lab_order=order,
                        test_field=field_def,
                        defaults={
                            'value': value_str,
                            'flag': flag,
                            'notes': res.get('notes', '')
                        }
                    )
                    saved_results.append(result_obj)
                
                # Update Order Status
                order.status = 'LAB_COMPLETED'
                order.performed_by = request.user.id
                order.completed_at = timezone.now()
                order.save()
                
                # Update Visit Status
                from .services import WorkflowService
                try:
                    WorkflowService.transition_visit(order.visit, 'LAB_COMPLETED')
                except ValueError:
                    pass

                # NEW: Trigger Kafka Event for Pet Owner Sync
                producer.send_event('VET_LAB_RESULT_PUBLISHED', {
                    'visit_id': str(order.visit.id),
                    'pet_id': str(order.visit.pet.id),
                    'pet_external_id': getattr(order.visit.pet, 'external_id', None),
                    'owner_auth_id': getattr(order.visit.pet.owner, 'auth_user_id', None),
                    'order_id': str(order.id),
                    'template_name': order.template.name,
                    'results': [
                        {
                            'field': r.test_field.field_name,
                            'value': r.value,
                            'unit': r.test_field.unit,
                            'flag': r.flag
                        } for r in saved_results
                    ],
                    'completed_at': order.completed_at.isoformat() if order.completed_at else None
                })

            return Response({'status': 'success', 'order_status': order.status})
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class StaffAssignmentViewSet(viewsets.ModelViewSet):
    """
    Manage Staff Clinic Assignments.
    GET /veterinary/assignments/?staff_id=uuid
    POST /veterinary/assignments/
    """
    from .models import StaffClinicAssignment
    from .serializers import StaffClinicAssignmentSerializer
    queryset = StaffClinicAssignment.objects.all()
    serializer_class = StaffClinicAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        user = self.request.user
        clinic_id = self.request.query_params.get('clinic')

        # [SENIOR DEV FIX] Allow Pet Owners (CUSTOMER) to read doctor fees for booking
        user_role = str(getattr(user, 'role', '')).upper()
        
        # If a clinic is specified, allow any authenticated user to see its staff (Read-only)
        if clinic_id:
            from django.db.models import Q
            clinic = Clinic.objects.filter(Q(id=clinic_id) | Q(organization_id=clinic_id)).first()
            
            if not clinic and str(clinic_id) == 'e957cb9e-0384-45e2-969a-b1fbd964a5f5':
                 clinic = Clinic.objects.filter(name__icontains='Gopi').first()

            if clinic:
                return self.queryset.filter(clinic=clinic)

        # Fallback to org-based filtering for management views
        org_id = None
        if hasattr(self.request, 'auth') and self.request.auth is not None:
            try:
                org_id = self.request.auth.get('user_id')
            except (AttributeError, TypeError):
                pass
        
        if not org_id and user and user.is_authenticated:
            org_id = str(user.username)
        
        if not org_id:
            return self.queryset.none()

        org_id = str(org_id)
        qs = self.queryset.filter(clinic__organization_id=org_id)

        # Optional: Filter by specific staff member
        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            qs = qs.filter(staff__auth_user_id=staff_id)

        return qs

    def perform_create(self, serializer):
        # [SENIOR DEV FIX] Enforce organization ownership of the target clinic
        user = self.request.user
        # Use username (UUID) not id (integer PK)
        org_id = str(user.username)
        if hasattr(self.request, 'auth') and self.request.auth is not None:
            try:
                token_user_id = self.request.auth.get('user_id')
                if token_user_id:
                    org_id = str(token_user_id)
            except (AttributeError, TypeError):
                pass
             
        clinic = serializer.validated_data.get('clinic')
        if clinic and str(clinic.organization_id) != str(org_id):
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("You can only assign staff to clinics you own.")
             
        serializer.save()


class MedicalAppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor-based medical appointments.
    """
    serializer_class = MedicalAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        queryset = MedicalAppointment.objects.none()
        if clinic_id:
            queryset = MedicalAppointment.objects.filter(clinic_id=clinic_id)
            
            date_from = self.request.query_params.get('date_from')
            date_to = self.request.query_params.get('date_to')
            
            if date_from:
                queryset = queryset.filter(appointment_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(appointment_date__lte=date_to)
                
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Custom create to use VeterinaryAppointmentService for atomic safety.
        """
        logic_request = {
            'clinic_id': get_clinic_context(request),
            'service_id': request.data.get('service_id'),
            'pet_id': request.data.get('pet_id'),
            'appointment_date': request.data.get('appointment_date'),
            'start_time': request.data.get('start_time'),
            'doctor_auth_id': request.data.get('doctor_auth_id'),
            'created_by': request.data.get('created_by', 'ONLINE'),
            'notes': request.data.get('notes'),
            'consultation_type': request.data.get('consultation_type', ''),
            'consultation_fee': request.data.get('consultation_fee', 0.00),
            'consultation_type_id': request.data.get('consultation_type_id')
        }

        if not logic_request['clinic_id']:
            return Response({'error': 'No clinic context'}, status=400)

        try:
            appointment = VeterinaryAppointmentService.create_appointment(**logic_request)
            return Response(MedicalAppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def internal_clinic_appointments(self, request):
        """
        Internal endpoint for service_provider_service to check ALL occupied slots in a clinic.
        """
        clinic_id = request.query_params.get('clinic_id')
        date_str = request.query_params.get('date')

        if not clinic_id or not date_str:
            return Response({"error": "clinic_id and date required"}, status=400)

        appointments = MedicalAppointment.objects.filter(
            clinic_id=clinic_id,
            appointment_date=date_str,
            status__in=['CONFIRMED', 'PENDING', 'IN_PROGRESS']
        )

        results = []
        for appt in appointments:
            results.append({
                'start': appt.start_time.strftime('%H:%M'),
                'end': appt.end_time.strftime('%H:%M'),
                'service_id': str(appt.service_id)
            })

        return Response(results)

    @action(detail=False, methods=['get'])
    def internal_doctor_appointments(self, request):
        """
        Internal endpoint for service_provider_service to check occupied slots.
        """
        doctor_auth_id = request.query_params.get('doctor_auth_id')
        date_str = request.query_params.get('date')

        if not doctor_auth_id or not date_str:
            return Response({"error": "doctor_auth_id and date required"}, status=400)

        appointments = MedicalAppointment.objects.filter(
            doctor__staff__auth_user_id=doctor_auth_id,
            appointment_date=date_str,
            status__in=['CONFIRMED', 'PENDING', 'IN_PROGRESS']
        )

        slots = []
        for appt in appointments:
            slots.append({
                'start': appt.start_time.strftime('%H:%M'),
                'end': appt.end_time.strftime('%H:%M')
            })

        return Response(slots)

    @action(detail=False, methods=['get'])
    def today_online(self, request):
        """
        Fetch today's ONLINE appointments for the logged-in doctor.
        """
        clinic_id = get_clinic_context(request)
        doctor_auth_id = get_auth_user_id(request)
        
        from django.utils import timezone
        today = timezone.now().date()
        
        appointments = MedicalAppointment.objects.filter(
            clinic_id=clinic_id,
            doctor__staff__auth_user_id=doctor_auth_id,
            appointment_date=today,
            consultation_mode='ONLINE'
        ).order_by('start_time')
        
        return Response(MedicalAppointmentSerializer(appointments, many=True).data)

    @action(detail=False, methods=['post'])
    def doctor_status(self, request):
        """
        Toggle doctor's online availability status.
        Body: { "available": true }
        """
        clinic_id = get_clinic_context(request)
        doctor_auth_id = get_auth_user_id(request)
        
        is_available = request.data.get('available', False)
        
        # In a real system, you might have multiple assignments, this updates the active one for the clinic
        updated = StaffClinicAssignment.objects.filter(
            clinic_id=clinic_id,
            staff__auth_user_id=doctor_auth_id,
            is_active=True
        ).update(is_online_available=is_available)
        
        if updated:
            return Response({"status": "success", "available": is_available})
        return Response({"error": "Staff assignment not found"}, status=404)

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        """
        Check-in a scheduled appointment.
        Creates a Visit if not exists and transitions status.
        """
        appointment = self.get_object()
        clinic_id = get_clinic_context(request)
        user_id = get_auth_user_id(request)

        # 1. State check to prevent duplicate check-in
        if appointment.status in ['CHECKED_IN', 'IN_PROGRESS', 'COMPLETED']:
            from rest_framework import status
            return Response({'error': 'Patient is already checked in or visit is already active.'}, status=status.HTTP_400_BAD_REQUEST)

        if appointment.status != 'CONFIRMED' and appointment.status != 'SCHEDULED':
             from rest_framework import status
             return Response({'error': f'Cannot check-in appointment in {appointment.status} status.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Support doctor assignment during check-in if provided
            doctor_auth_id = request.data.get('assigned_doctor_auth_id') or appointment.doctor_auth_id
            
            if not doctor_auth_id:
                from rest_framework import status
                return Response({'error': 'Doctor assignment is mandatory for check-in.'}, status=status.HTTP_400_BAD_REQUEST)

            if doctor_auth_id != appointment.doctor_auth_id:
                appointment.doctor_auth_id = doctor_auth_id
                appointment.save(update_fields=['doctor_auth_id'])

            # 2. Create Visit if not exists
            visit, created = Visit.objects.get_or_create(
                appointment=appointment,
                defaults={
                    'clinic_id': clinic_id or appointment.clinic_id,
                    'pet': appointment.pet,
                    'service_id': appointment.service_id,
                    'status': 'CREATED',
                    'reason': appointment.notes,
                    'created_by': user_id,
                    'assigned_doctor_auth_id': doctor_auth_id
                }
            )

            if not created and doctor_auth_id:
                visit.assigned_doctor_auth_id = doctor_auth_id
                visit.save(update_fields=['assigned_doctor_auth_id'])

            # 2. Transition status for both
            from .services import WorkflowService
            WorkflowService.transition_visit(visit, 'CHECKED_IN', user_role=user_id)
            
            # Note: Transitioning the Visit status triggers the appointment status change via signals/logic
            # If not, we do it explicitly:
            appointment.status = 'COMPLETED' # In some systems, appointment is completed when visit starts
            # But in this system, let's keep it 'CONFIRMED' or maybe add a new status 'ARRIVED'
            # Let's check MedicalAppointment statuses
            # ('CONFIRMED', 'Cancelled', 'Completed')
            # Typically 'WAITING' is a Visit status.
            appointment.save()

        return Response({
            'status': 'success',
            'visit_id': str(visit.id),
            'visit_status': visit.status
        })


class VeterinaryAvailabilityViewSet(viewsets.ViewSet):
    """
    Endpoints for veterinary doctor-specific availability.
    """
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'], url_path='(?P<clinic_id>[^/.]+)/slots')
    def get_slots(self, request, clinic_id=None):
        service_id = request.query_params.get('service_id')
        date_str = request.query_params.get('date')
        doctor_auth_id = request.query_params.get('doctor_auth_id')
        consultation_type_id = request.query_params.get('consultation_type_id')

        if not service_id or not date_str:
            return Response({"error": "service_id and date are required"}, status=400)

        slots = VeterinaryAvailabilityService.get_doctor_available_slots(
            clinic_id, service_id, date_str, doctor_auth_id, consultation_type_id
        )
        return Response({"slots": slots})


from rest_framework import views
from datetime import timedelta
from django.db import transaction
from .models import Clinic, StaffClinicAssignment, Pet, PetOwner, Visit, MedicalAppointment
from .serializers import MedicalAppointmentSerializer
from rest_framework.response import Response
from rest_framework import status, permissions

class CreateOnlineAppointmentView(views.APIView):
    """
    Internal endpoint called by customer_service when a vet booking is confirmed.
    Creates a MedicalAppointment (and optionally a Visit) without requiring a
    vet-service auth token — uses AllowAny and validates via a shared secret header.

    POST /api/veterinary/internal/create-online-appointment/
    Body: {
        booking_id, clinic_id, doctor_auth_id, pet_owner_auth_id,
        pet_external_id, service_id,
        appointment_date, start_time, end_time (optional),
        consultation_type, notes
    }
    """
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        from datetime import datetime, timedelta
        data = request.data
        required = ['booking_id', 'clinic_id', 'doctor_auth_id', 'pet_external_id',
                    'service_id', 'appointment_date', 'start_time']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return Response({'error': f'Missing fields: {missing}'}, status=400)

        # ── Avoid duplicate appointments for the same booking ──────────────────
        booking_id = data['booking_id']
        if MedicalAppointment.objects.filter(online_booking_id=booking_id).exists():
            appt = MedicalAppointment.objects.get(online_booking_id=booking_id)
            return Response(MedicalAppointmentSerializer(appt).data, status=200)

        # ── Resolve clinic ─────────────────────────────────────────────────────
        # clinic_id in payload is the provider_auth_id (organization_id)
        clinic = Clinic.objects.filter(organization_id=data['clinic_id']).first()
        if not clinic:
            return Response({'error': f"Clinic for provider {data['clinic_id']} not found. "
                             "Ensure the provider has a clinic created in veterinary_service."}, status=404)

        # ── Resolve doctor via StaffClinicAssignment ───────────────────────────
        doctor_auth_id = data['doctor_auth_id']
        doctor_assignment = StaffClinicAssignment.objects.filter(
            clinic=clinic,
            staff__auth_user_id=doctor_auth_id,
            is_active=True
        ).first()
        if not doctor_assignment:
            return Response({'error': f"No active StaffClinicAssignment found for doctor {doctor_auth_id} "
                             f"in clinic {clinic.id}"}, status=404)

        # ── Resolve pet ────────────────────────────────────────────────────────
        pet_external_id = data['pet_external_id']
        pet = Pet.objects.filter(external_id=pet_external_id).first() or \
              Pet.objects.filter(id=pet_external_id).first()
        
        # Sync Pet Owner info
        pet_owner_auth = data.get('pet_owner_auth_id', '')
        owner, _ = PetOwner.objects.update_or_create(
            clinic=clinic,
            auth_user_id=pet_owner_auth or None,
            defaults={
                'name': data.get('owner_name', 'Online Pet Owner'),
                'phone': data.get('owner_phone', 'online-booking'),
                'email': data.get('owner_email', ''),
            }
        )

        if not pet:
            # Create pet with full details
            # Ensure weight is a float and handle potential 'None' string from malformed payload
            try:
                raw_weight = data.get('weight_kg', 0)
                pet_weight = float(raw_weight) if raw_weight and str(raw_weight).lower() != 'none' else 0
            except (ValueError, TypeError):
                pet_weight = 0

            pet = Pet.objects.create(
                id=pet_external_id if len(str(pet_external_id)) == 36 else None,
                external_id=pet_external_id,
                owner=owner,
                name=data.get('pet_name', 'Pet (Online Booking)'),
                species=data.get('species', 'DOG').upper(),
                breed=data.get('breed', ''),
                sex=data.get('gender', 'MALE').upper(),
                dob=data.get('date_of_birth'),
                weight=pet_weight,
            )
        else:
            # Update existing pet with potentially newer clinical info
            pet.name = data.get('pet_name', pet.name)
            pet.species = data.get('species', pet.species).upper()
            pet.breed = data.get('breed', pet.breed)
            pet.sex = data.get('gender', pet.sex).upper()
            if data.get('date_of_birth'):
                pet.dob = data.get('date_of_birth')
            if data.get('weight_kg'):
                try:
                    raw_w = data['weight_kg']
                    pet.weight = float(raw_w) if raw_w and str(raw_w).lower() != 'none' else pet.weight
                except (ValueError, TypeError):
                    pass
            pet.owner = owner
            pet.save()

        # ── Build appointment times ────────────────────────────────────────────
        appointment_date = data['appointment_date']
        start_time_str = data['start_time']
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        # Default end_time = start + 30 min
        end_time_str = data.get('end_time')
        if end_time_str:
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        else:
            start_dt = datetime.combine(datetime.today().date(), start_time)
            end_time = (start_dt + timedelta(minutes=30)).time()

        # ── Create MedicalAppointment ──────────────────────────────────────────
        appointment = MedicalAppointment.objects.create(
            clinic=clinic,
            doctor=doctor_assignment,
            pet=pet,
            service_id=data['service_id'],
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            status='CONFIRMED',
            created_by='ONLINE',
            notes=data.get('notes', ''),
            online_booking_id=data.get('booking_id'),
            pet_owner_auth_id=data.get('pet_owner_auth_id', ''),
            consultation_type=data.get('consultation_type', ''),
            consultation_fee=data.get('consultation_fee', 0.00),
            consultation_type_id=data.get('consultation_type_id') or None
        )

        # ── Create corresponding Visit record ──────────────────────────────────
        visit = Visit.objects.create(
            clinic=clinic,
            pet=pet,
            appointment=appointment,
            visit_type='ONLINE',
            status='CREATED',
            reason=data.get('consultation_type') or data.get('notes') or 'Online Booking',
            service_id=str(data['service_id']),
        )
        return Response(MedicalAppointmentSerializer(appointment).data, status=201)

# ========================
# NEXT GEN ENGINE VIEWSETS
# ========================

class LabTestViewSet(viewsets.ModelViewSet):
    """Catalog of lab tests available for order."""
    queryset = LabTest.objects.all()
    serializer_class = LabTestSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            # Show global templates (clinic=null) or clinic-specific tests
            from django.db.models import Q
            return LabTest.objects.filter(Q(clinic_id=clinic_id) | Q(clinic__isnull=True), is_active=True)
        return LabTest.objects.none()

class MedicineViewSet(viewsets.ModelViewSet):
    """Catalog and Inventory of medicines."""
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return Medicine.objects.filter(clinic_id=clinic_id, is_active=True)
        return Medicine.objects.none()

    def perform_create(self, serializer):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No clinic context found. Cannot create medicine.")
        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"clinic": "Clinic not found."})
        serializer.save(clinic=clinic)

    def perform_update(self, serializer):
        # Prevent clinic from being changed on update
        serializer.save()

class PrescriptionViewSet(viewsets.ModelViewSet):
    """Formal prescriptions issued during visits."""
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return Prescription.objects.filter(visit__clinic_id=clinic_id).order_by('-created_at')
        return Prescription.objects.none()

    def perform_create(self, serializer):
        instance = serializer.save()
        
        # NEW: Trigger Kafka Event for Pet Owner Sync
        producer.send_event('VET_PRESCRIPTION_CREATED', {
            'prescription_id': str(instance.id),
            'visit_id': str(instance.visit.id),
            'pet_id': str(instance.visit.pet.id),
            'pet_external_id': getattr(instance.visit.pet, 'external_id', None),
            'owner_auth_id': getattr(instance.visit.pet.owner, 'auth_user_id', None),
            'medicine_name': instance.medicine_name,
            'dosage': instance.dosage,
            'duration_days': instance.duration_days,
            'notes': instance.notes
        })

    @action(detail=True, methods=['post'], url_path='upload_prescription')
    def upload_prescription(self, request, pk=None):
        """
        Uploads a PDF prescription file.
        Body: FormData with 'prescription_file'
        """
        prescription = self.get_object()
        file = request.FILES.get('prescription_file')
        
        if not file:
            return Response({"error": "No file provided"}, status=400)
            
        prescription.prescription_file = file
        prescription.save()
        
        return Response({"status": "success", "file_url": prescription.prescription_file.url})

class PharmacyTransactionViewSet(viewsets.ModelViewSet):
    """Audit log of medicines dispensed."""
    queryset = PharmacyTransaction.objects.all()
    serializer_class = PharmacyTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return PharmacyTransaction.objects.filter(visit__clinic_id=clinic_id).order_by('-created_at')
        return PharmacyTransaction.objects.none()

    def create(self, request, *args, **kwargs):
        """Custom create to use PharmacyService dispensing logic with stock reduction."""
        visit_id = request.data.get('visit')
        medicine_id = request.data.get('medicine')
        quantity = request.data.get('quantity')
        
        if not all([visit_id, medicine_id, quantity]):
            return Response({"error": "visit, medicine, and quantity are required"}, status=400)
            
        try:
            txn = PharmacyService.dispense_medical_item(
                visit_id=visit_id,
                medicine_id=medicine_id,
                quantity=float(quantity),
                user_id=request.user.id
            )
            return Response(PharmacyTransactionSerializer(txn).data, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class VisitInvoiceViewSet(viewsets.ModelViewSet):
    """Consolidated billing invoices."""
    queryset = VisitInvoice.objects.all()
    serializer_class = VisitInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess, VeterinaryCheckoutPermission]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return VisitInvoice.objects.filter(visit__clinic_id=clinic_id).order_by('-created_at')
        return VisitInvoice.objects.none()

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = 'PAID'
        invoice.save()
        
        # Log audit trail
        from .models import VeterinaryAuditLog
        VeterinaryAuditLog.objects.create(
            visit=invoice.visit,
            action_type='INVOICE_PAID',
            performed_by=request.user.id,
            metadata={"total": str(invoice.total)}
        )
        return Response({"status": "Invoice marked as paid"})

# ==========================================
# PHASE 5: VACCINATION TRACKING VIEWSETS
# ==========================================

from .models import VaccineMaster, PetVaccinationRecord, VaccinationReminder
from .serializers import (
    VaccineMasterSerializer, PetVaccinationRecordSerializer, VaccinationReminderSerializer
)
from rest_framework.decorators import action

class VaccineMasterViewSet(viewsets.ModelViewSet):
    """
    Manage the master list of vaccines for the clinic.
    """
    serializer_class = VaccineMasterSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]
    
    @require_capability(['analytics.view', 'vaccination.*'])
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            return VaccineMaster.objects.none()
        return VaccineMaster.objects.filter(clinic_id=clinic_id)

    def perform_create(self, serializer):
        clinic_id = get_clinic_context(self.request)
        serializer.save(clinic_id=clinic_id)


class PetVaccinationRecordViewSet(viewsets.ModelViewSet):
    """
    Manage individual pet vaccination records.
    """
    serializer_class = PetVaccinationRecordSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @require_capability(['consultation.*', 'vaccination.*'])
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            return PetVaccinationRecord.objects.none()
            
        qs = PetVaccinationRecord.objects.filter(clinic_id=clinic_id).order_by('next_due_date')
        
        pet_id = self.request.query_params.get('pet_id')
        if pet_id:
            qs = qs.filter(pet_id=pet_id)
            
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
            
        return qs

    def perform_create(self, serializer):
        clinic_id = get_clinic_context(self.request)
        user_auth_id = str(self.request.user.id)
        if hasattr(self.request.auth, 'get'):
             user_auth_id = self.request.auth.get('user_id') or user_auth_id
             
        record = serializer.save(clinic_id=clinic_id, doctor=user_auth_id)
        
        if record.status == 'SCHEDULED' and record.next_due_date:
            from datetime import timedelta
            reminder_date = record.next_due_date - timedelta(days=7)
            VaccinationReminder.objects.create(
                vaccination_record=record,
                reminder_date=reminder_date,
                reminder_type='SMS'
            )

    @action(detail=True, methods=['patch'])
    def mark_completed(self, request, pk=None):
        """
        Mark a scheduled vaccination as completed today.
        """
        record = self.get_object()
        if record.status == 'COMPLETED':
             return Response({"error": "Already completed"}, status=status.HTTP_400_BAD_REQUEST)
             
        from datetime import date
        record.status = 'COMPLETED'
        record.administered_date = date.today()
        
        user_auth_id = str(self.request.user.id)
        if hasattr(self.request.auth, 'get'):
             user_auth_id = self.request.auth.get('user_id') or user_auth_id
             
        record.doctor = user_auth_id
        record.batch_number = request.data.get('batch_number', record.batch_number)
        record.save()
        
        record.reminders.update(sent_status=True)
        return Response(self.get_serializer(record).data)

    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """
        Return vaccinations due within the next 30 days.
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
            return Response([])
            
        from datetime import date, timedelta
        today = date.today()
        thirty_days = today + timedelta(days=30)
        
        qs = PetVaccinationRecord.objects.filter(
            clinic_id=clinic_id,
            status='SCHEDULED',
            next_due_date__range=[today, thirty_days]
        ).order_by('next_due_date')
        
        pet_id = request.query_params.get('pet_id')
        if pet_id:
            qs = qs.filter(pet_id=pet_id)
            
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

# ==========================================
# PHASE 6: ESTIMATE VIEWSETS
# ==========================================

from .models import TreatmentEstimate, EstimateLineItem
from .serializers import TreatmentEstimateSerializer, EstimateLineItemSerializer
from .services import EstimateService

class TreatmentEstimateViewSet(viewsets.ModelViewSet):
    queryset = TreatmentEstimate.objects.all()
    serializer_class = TreatmentEstimateSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return TreatmentEstimate.objects.filter(visit__clinic_id=clinic_id).order_by('-created_at')
        return TreatmentEstimate.objects.none()

    def perform_create(self, serializer):
        user_auth_id = str(self.request.user.id)
        if hasattr(self.request.auth, 'get'):
             user_auth_id = self.request.auth.get('user_id') or user_auth_id
        serializer.save(created_by=user_auth_id)

    @action(detail=True, methods=['post'])
    def convert_to_invoice(self, request, pk=None):
        """
        Manually trigger conversion to invoice.
        """
        user_auth_id = str(request.user.id)
        if hasattr(request.auth, 'get'):
             user_auth_id = request.auth.get('user_id') or user_auth_id
             
        try:
            invoice = EstimateService.convert_to_invoice(pk, user_auth_id)
            from .serializers import VisitInvoiceSerializer
            return Response(VisitInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class EstimateLineItemViewSet(viewsets.ModelViewSet):
    queryset = EstimateLineItem.objects.all()
    serializer_class = EstimateLineItemSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return EstimateLineItem.objects.filter(estimate__visit__clinic_id=clinic_id)
        return EstimateLineItem.objects.none()

# ==========================================
# PHASE 4: PRE-VISIT FORM VIEWSETS
# ==========================================

from .models import PreVisitForm
from .serializers import PreVisitFormSerializer
from django.utils import timezone

class PreVisitFormViewSet(viewsets.ModelViewSet):
    """
    Manage pre-visit check-in forms.
    Includes public endpoint for pet owners.
    """
    queryset = PreVisitForm.objects.all()
    serializer_class = PreVisitFormSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return PreVisitForm.objects.filter(visit__clinic_id=clinic_id).order_by('-created_at')
        return PreVisitForm.objects.none()

    @action(detail=False, methods=['get', 'post'], permission_classes=[permissions.AllowAny], url_path='public/(?P<token>[^/.]+)')
    def public_access(self, request, token=None):
        """
        Public endpoint for owners to view and submit the form via secure token.
        """
        try:
            form = PreVisitForm.objects.get(access_token=token)
        except PreVisitForm.DoesNotExist:
            return Response({"error": "Invalid or expired link."}, status=404)

        if request.method == 'GET':
            return Response(PreVisitFormSerializer(form).data)

        if request.method == 'POST':
            if form.is_submitted:
                return Response({"error": "Form already submitted."}, status=400)
            
            form.data = request.data.get('data', {})
            form.is_submitted = True
            form.submitted_at = timezone.now()
            form.save()
            return Response({"message": "Check-in successful. Thank you!"})

# ==========================================
# PHASE 7: VACCINATION & DEWORMING REMINDER SYSTEM VIEWSETS
# ==========================================

from .models import Vaccination, SystemVaccinationReminder, Deworming, SystemDewormingReminder
from .serializers import (
    VaccinationSerializer, SystemVaccinationReminderSerializer, 
    DewormingSerializer, SystemDewormingReminderSerializer
)
from datetime import timedelta

class SystemVaccinationReminderViewSet(viewsets.ModelViewSet):
    queryset = SystemVaccinationReminder.objects.all()
    serializer_class = SystemVaccinationReminderSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return SystemVaccinationReminder.objects.filter(pet__owner__clinic_id=clinic_id).order_by('reminder_date')
        return SystemVaccinationReminder.objects.none()

class VaccinationViewSet(viewsets.ModelViewSet):
    queryset = Vaccination.objects.all()
    serializer_class = VaccinationSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            qs = Vaccination.objects.filter(pet__owner__clinic_id=clinic_id).order_by('-date_given')
            pet_id = self.request.query_params.get('pet_id')
            if pet_id:
                qs = qs.filter(pet_id=pet_id)
            return qs
        return Vaccination.objects.none()

    def perform_create(self, serializer):
        user_auth_id = str(self.request.user.id)
        if hasattr(self.request.auth, 'get'):
             user_auth_id = self.request.auth.get('user_id') or user_auth_id
             
        vaccination = serializer.save(doctor_id=user_auth_id)
        
        # NEW: Trigger Kafka Event for Pet Owner Sync
        producer.send_event('VET_VACCINATION_RECORDED', {
            'vaccination_id': str(vaccination.id),
            'pet_id': str(vaccination.pet.id),
            'pet_external_id': getattr(vaccination.pet, 'external_id', None),
            'owner_auth_id': getattr(vaccination.pet.owner, 'auth_user_id', None),
            'vaccine_name': vaccination.vaccine_name,
            'date_given': vaccination.date_given.isoformat() if vaccination.date_given else None,
            'next_due_date': vaccination.next_due_date.isoformat() if vaccination.next_due_date else None
        })
        
        # Automatically generate reminders (7 days and 1 day before)
        if vaccination.next_due_date:
            SystemVaccinationReminder.objects.create(
                pet=vaccination.pet,
                pet_owner_id=vaccination.pet.owner.auth_user_id or "UNKNOWN",
                vaccine_name=vaccination.vaccine_name,
                next_due_date=vaccination.next_due_date,
                reminder_date=vaccination.next_due_date - timedelta(days=7),
                status='PENDING'
            )
            SystemVaccinationReminder.objects.create(
                pet=vaccination.pet,
                pet_owner_id=vaccination.pet.owner.auth_user_id or "UNKNOWN",
                vaccine_name=vaccination.vaccine_name,
                next_due_date=vaccination.next_due_date,
                reminder_date=vaccination.next_due_date - timedelta(days=1),
                status='PENDING'
            )

class SystemDewormingReminderViewSet(viewsets.ModelViewSet):
    queryset = SystemDewormingReminder.objects.all()
    serializer_class = SystemDewormingReminderSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return SystemDewormingReminder.objects.filter(pet__owner__clinic_id=clinic_id).order_by('reminder_date')
        return SystemDewormingReminder.objects.none()

class DewormingViewSet(viewsets.ModelViewSet):
    queryset = Deworming.objects.all()
    serializer_class = DewormingSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            qs = Deworming.objects.filter(pet__owner__clinic_id=clinic_id).order_by('-date_given')
            pet_id = self.request.query_params.get('pet_id')
            if pet_id:
                qs = qs.filter(pet_id=pet_id)
            return qs
        return Deworming.objects.none()

    def perform_create(self, serializer):
        user_auth_id = str(self.request.user.id)
        if hasattr(self.request.auth, 'get'):
             user_auth_id = self.request.auth.get('user_id') or user_auth_id
             
        deworming = serializer.save(doctor_id=user_auth_id)
        
        # Automatically generate reminders (7 days and 1 day before)
        if deworming.next_due_date:
            SystemDewormingReminder.objects.create(
                pet=deworming.pet,
                pet_owner_id=deworming.pet.owner.auth_user_id or "UNKNOWN",
                medicine_name=deworming.medicine_name,
                next_due_date=deworming.next_due_date,
                reminder_date=deworming.next_due_date - timedelta(days=7),
                status='PENDING'
            )
            SystemDewormingReminder.objects.create(
                pet=deworming.pet,
                pet_owner_id=deworming.pet.owner.auth_user_id or "UNKNOWN",
                medicine_name=deworming.medicine_name,
                next_due_date=deworming.next_due_date,
                reminder_date=deworming.next_due_date - timedelta(days=1),
                status='PENDING'
            )


# ========================
# PHASE 7: DASHBOARD APIs
# ========================

class DashboardViewSet(viewsets.ViewSet):
    """
    Aggregate Clinic Analytics for Real-time Dashboard.
    """
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        clinic_id = get_clinic_context(request)
        if not clinic_id:
            return Response({"detail": "Clinic context missing."}, status=400)
            
        date_param = request.query_params.get('date')
        service_id = request.query_params.get('service_id')
        
        metrics = ClinicAnalyticsService.get_dashboard_metrics(
            clinic_id=clinic_id,
            date_param=date_param,
            service_id=service_id
        )
        
        return Response(metrics)

    @action(detail=False, methods=['get'])
    def live_summary(self, request):
        clinic_id = get_clinic_context(request)
        if not clinic_id:
            return Response({"detail": "Clinic context missing."}, status=400)
            
        date_param = request.query_params.get('date')
        summary = ClinicAnalyticsService.get_live_summary(
            clinic_id=clinic_id,
            date_param=date_param
        )
        return Response(summary)

# ========================
# SAAS PHARMACY ORDER FULFILLMENT VIEWSET
# ========================

class PharmacyOrderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_order_data(self, order):
        items = []
        for item in order.items.select_related('medicine').all():
            items.append({
                'id': str(item.id),
                'medicine_id': str(item.medicine.id),
                'medicine_name': item.medicine.name,
                'quantity_prescribed': float(item.quantity_prescribed),
                'quantity_dispensed': float(item.quantity_dispensed),
                'unit_price': float(item.unit_price),
                'available_stock': float(item.medicine.stock_quantity),
                'is_available': item.is_available,
            })
        return {
            'id': str(order.id),
            'pet_name': order.pet_name,
            'owner_name': order.owner_name,
            'owner_phone': order.owner_phone,
            'owner_email': order.owner_email,
            'status': order.status,
            'total_amount': float(order.total_amount),
            'created_at': order.created_at.isoformat(),
            'completed_at': order.completed_at.isoformat() if order.completed_at else None,
            'items': items,
        }

    def list(self, request):
        from .models import PharmacyOrder
        clinic_id = get_clinic_context(request)
        qs = PharmacyOrder.objects.filter(
            clinic_id=clinic_id
        ).exclude(status='COMPLETED').order_by('-created_at').prefetch_related('items__medicine')
        return Response([self._get_order_data(o) for o in qs])

    def retrieve(self, request, pk=None):
        from .models import PharmacyOrder
        try:
            order = PharmacyOrder.objects.prefetch_related('items__medicine').get(id=pk)
            return Response(self._get_order_data(order))
        except PharmacyOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='check-stock')
    def check_stock(self, request, pk=None):
        from .services import PharmacyFulfillmentService
        try:
            order = PharmacyFulfillmentService.check_stock(pk, get_auth_user_id(request))
            return Response(self._get_order_data(order))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='partial-approve')
    def partial_approve(self, request, pk=None):
        from .services import PharmacyFulfillmentService
        try:
            quantities = request.data.get('quantities', {})
            order = PharmacyFulfillmentService.approve_partial(pk, quantities, get_auth_user_id(request))
            return Response(self._get_order_data(order))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='send-otp')
    def send_otp(self, request, pk=None):
        from .services import PharmacyFulfillmentService
        try:
            otp = PharmacyFulfillmentService.send_otp(pk, get_auth_user_id(request))
            # In dev/testing, we expose the OTP in the response. Remove in prod.
            return Response({'message': 'OTP sent', 'dev_otp': otp.otp_code})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='verify-otp')
    def verify_otp(self, request):
        from .services import PharmacyFulfillmentService
        try:
            order_id = request.data.get('order_id')
            otp_code = request.data.get('otp_code')
            order = PharmacyFulfillmentService.verify_otp(order_id, otp_code, get_auth_user_id(request))
            return Response(self._get_order_data(order))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        from .services import PharmacyFulfillmentService
        try:
            order = PharmacyFulfillmentService.complete_order(pk, get_auth_user_id(request))
            return Response(self._get_order_data(order))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='add-medicine')
    def add_medicine(self, request, pk=None):
        """Add a medicine item to a PENDING pharmacy order."""
        from .models import PharmacyOrder, PharmacyOrderItem, Medicine
        try:
            order = PharmacyOrder.objects.get(id=pk)
            if order.status not in ['PENDING', 'STOCK_CHECKED']:
                return Response({'error': 'Can only add medicines to PENDING or STOCK_CHECKED orders.'}, status=400)

            medicine_name = request.data.get('medicine_name', '').strip()
            quantity = float(request.data.get('quantity', 1))
            unit_price = float(request.data.get('unit_price', 0))

            med = Medicine.objects.filter(
                clinic=order.clinic, name__iexact=medicine_name, is_active=True
            ).first()
            if not med:
                # Create a placeholder medicine in the clinic catalog
                med = Medicine.objects.create(
                    clinic=order.clinic,
                    name=medicine_name,
                    stock_quantity=0,
                    unit_price=unit_price or 0,
                )

            item, created = PharmacyOrderItem.objects.get_or_create(
                order=order, medicine=med,
                defaults={'quantity_prescribed': quantity, 'unit_price': unit_price}
            )
            if not created:
                item.quantity_prescribed = quantity
                item.unit_price = unit_price
                item.save()

            # Reset order to PENDING so stock check runs again
            if order.status == 'STOCK_CHECKED':
                order.status = 'PENDING'
                order.save()

            return Response(self._get_order_data(order))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove-medicine/(?P<item_id>[^/.]+)')
    def remove_medicine(self, request, pk=None, item_id=None):
        """Remove a medicine item from a PENDING pharmacy order."""
        from .models import PharmacyOrder, PharmacyOrderItem
        try:
            order = PharmacyOrder.objects.get(id=pk)
            if order.status not in ['PENDING', 'STOCK_CHECKED']:
                return Response({'error': 'Can only remove medicines from PENDING orders.'}, status=400)
            PharmacyOrderItem.objects.filter(id=item_id, order=order).delete()
            return Response(self._get_order_data(order))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class MedicineViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            return Medicine.objects.none()
        return Medicine.objects.filter(clinic_id=clinic_id).prefetch_related('batches')

    def perform_create(self, serializer):
        clinic_id = self.request.data.get('clinic_id') or get_clinic_context(self.request)
        serializer.save(clinic_id=clinic_id)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        clinic_id = get_clinic_context(request)
        if not clinic_id:
            return Response({'error': 'clinic_id required'}, status=400)
        # Filter where stock_quantity <= low_stock_threshold
        medicines = Medicine.objects.filter(
            clinic_id=clinic_id,
            stock_quantity__lte=models.F('low_stock_threshold')
        )
        return Response(MedicineSerializer(medicines, many=True).data)

class MedicineBatchViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = MedicineBatch.objects.all()
        medicine_id = self.request.query_params.get('medicine_id')
        clinic_id = get_clinic_context(self.request)
        
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)
        if clinic_id:
            queryset = queryset.filter(medicine__clinic_id=clinic_id)
            
        if not medicine_id and not clinic_id:
            return MedicineBatch.objects.none()
            
        return queryset

    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        clinic_id = get_clinic_context(request)
        if not clinic_id:
            return Response({'error': 'clinic_id required'}, status=400)
        days = int(request.query_params.get('days', 30))
        from django.utils import timezone
        cutoff = timezone.now().date() + timezone.timedelta(days=days)
        batches = MedicineBatch.objects.filter(
            medicine__clinic_id=clinic_id,
            expiry_date__lte=cutoff,
            current_quantity__gt=0
        ).select_related('medicine')
        return Response(MedicineBatchSerializer(batches, many=True).data)
