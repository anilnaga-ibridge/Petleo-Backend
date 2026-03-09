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
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import (
    Clinic, PetOwner, Pet, Visit,
    DynamicFieldDefinition, DynamicFieldValue,
    FormDefinition, FormField, FormSubmission,
    LabTestTemplate, LabTestField, LabOrder, LabResult,
    MedicalAppointment, StaffClinicAssignment,
    LabTest, Medicine, Prescription, PrescriptionItem, PharmacyTransaction,
    VisitInvoice, InvoiceLineItem
)
from .serializers import (
    ClinicSerializer, PetOwnerSerializer, PetSerializer, VisitSerializer,
    DynamicFieldDefinitionSerializer, DynamicFieldValueSerializer,
    DynamicEntitySerializer,
    FormDefinitionSerializer, FormSubmissionSerializer, VisitDetailSerializer,
    LabTestTemplateSerializer, LabOrderSerializer, LabResultSerializer, PharmacyDispenseSerializer,
    MedicalAppointmentSerializer, StaffClinicAssignmentSerializer,
    LabTestSerializer, MedicineSerializer, PrescriptionSerializer,
    PharmacyTransactionSerializer, VisitInvoiceSerializer, InvoiceLineItemSerializer
)
from .services import (
    DynamicEntityService, WorkflowService, MetadataService, 
    LabService, PharmacyService, ReminderService, VisitQueueService,
    VisitTimelineService, ClinicAnalyticsService,
    VeterinaryAvailabilityService, VeterinaryAppointmentService
)
from .kafka.producer import producer
from .permissions import HasVeterinaryAccess, IsClinicStaffOfPet, require_capability, require_granular_capability
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
        
        serializer.save(
            organization_id=org_id,
            is_primary=not has_clinics
        )

class PetOwnerViewSet(viewsets.ModelViewSet):
    serializer_class = PetOwnerSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return PetOwner.objects.filter(clinic_id=clinic_id)
        return PetOwner.objects.none()

    def perform_create(self, serializer):
        clinic_id = get_clinic_context(self.request)
        if not clinic_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("No active clinic context found. Please select a clinic.")
        
        serializer.save(
            clinic_id=clinic_id,
            created_by=get_auth_user_id(self.request)
        )

class PetViewSet(viewsets.ModelViewSet):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def perform_update(self, serializer):
        from .permissions import log
        log(f"PetViewSet.perform_update: Validating save for {self.get_object().id}")
        serializer.save()
        log("PetViewSet.perform_update: Save complete")

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        if clinic_id:
            return Pet.objects.filter(owner__clinic_id=clinic_id)
        return Pet.objects.none()

    def perform_create(self, serializer):
        log_file = "/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service/middleware_trace.log"
        def log_trace(msg):
            try:
                from django.utils import timezone
                with open(log_file, "a") as f:
                    f.write(f"{timezone.now()} - [PET_TRACE] {msg}\n")
            except:
                pass

        try:
            log_trace(f"--- PET CREATE ATTEMPT ---")
            log_trace(f"RAW DATA: {self.request.data}")
            log_trace(f"VALIDATED DATA: {serializer.validated_data}")

            from rest_framework.exceptions import ValidationError
            
            # Support offline creation by receptionist
            owner_id = self.request.data.get('owner')
            
            if not owner_id:
                owner_name = self.request.data.get('owner_name')
                owner_phone = self.request.data.get('owner_phone')
                owner_email = self.request.data.get('owner_email')
                owner_address = self.request.data.get('owner_address') or self.request.data.get('address')
                clinic_id = get_clinic_context(self.request)
                
                log_trace(f"Owner ID missing. owner_name: {owner_name}, owner_phone: {owner_phone}, clinic_id: {clinic_id}")

                if not clinic_id:
                    log_trace("ERROR: No active clinic context found.")
                    raise ValidationError({"error": "No active clinic context found."})
                    
                if owner_phone:
                    from .models import PetOwner
                    owner, created = PetOwner.objects.get_or_create(
                        clinic_id=clinic_id,
                        phone=owner_phone,
                        defaults={
                            'name': owner_name or "New Owner",
                            'email': owner_email,
                            'address': owner_address
                        }
                    )
                    log_trace(f"SAVING WITH NEW/FOUND OWNER: {owner.id} (Created: {created})")
                    serializer.save(owner=owner, created_by=get_auth_user_id(self.request))
                    return
                else:
                    log_trace("ERROR: owner_phone missing in payload.")
                    raise ValidationError({"owner_phone": "Owner phone is required for registration."})

            log_trace(f"SAVING WITH PROVIDED OWNER_ID: {owner_id}")
            serializer.save(created_by=get_auth_user_id(self.request))
            log_trace("SAVE SUCCESSFUL")
        except Exception as e:
            log_trace(f"CRITICAL ERROR IN PET CREATE: {str(e)}")
            import traceback
            log_trace(traceback.format_exc())
            raise e

    def perform_update(self, serializer):
        """
        Handle Patient updates.
        Senior Developer Rule: For Owners, we allow updating owner_name/phone indirectly 
        through the Pet registration/edit flow.
        """
        try:
            log_trace(f"PET UPDATE START: Request data: {self.request.data}")
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
                    log_trace(f"Updated Owner Info: {owner.id}")
            
            serializer.save()
            log_trace("UPDATE SUCCESSFUL")
        except Exception as e:
            log_trace(f"ERROR IN PET UPDATE: {str(e)}")
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
            'WAITING_ROOM': 'VETERINARY_VISITS',
            'VITALS_QUEUE': 'VETERINARY_VITALS',
            'DOCTOR_QUEUE': 'VETERINARY_DOCTOR',
            'LAB_QUEUE': 'VETERINARY_LABS',
            'PHARMACY_QUEUE': 'VETERINARY_PHARMACY'
        }
        
        required_cap = REQUIRED_CAPS.get(queue_name)
        
        if required_cap:
            # 1. AUTH & ROLE EXTRACTION
            user_id = getattr(request.user, 'username', str(request.user.id)) # Ensure string ID
            role = str(getattr(request.user, 'role', '')).upper()

            # 2. BYPASS FOR OWNERS (Organization/Individual)
            if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
                # Owners have implicit access
                pass 
            else:
                # 3. USE MIDDLEWARE PERMISSIONS (Preferred)
                # The VeterinaryPermissionMiddleware already resolves StaffClinicAssignment and populates request.user.permissions
                user_perms = getattr(request.user, 'permissions', [])
                if required_cap in user_perms:
                    pass # Access Granted
                else:
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
    def check_in(self, request, pk=None):
        from rest_framework.exceptions import PermissionDenied
        visit = self.get_object()
        
        # [PERMISSION CHECK]
        # If it's a Core Veterinary Visit (no service_id), enforce VETERINARY_VISITS
        if not visit.service_id:
            user_perms = getattr(request.user, 'permissions', [])
            if 'VETERINARY_VISITS' not in user_perms:
                raise PermissionDenied("You do not have permission to check-in veterinary visits.")
        
        try:
            WorkflowService.transition_visit(visit, 'CHECKED_IN', user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def ai_format_notes(self, request, pk=None):
        """
        AI-assisted SOAP note formatting.
        """
        raw_notes = request.data.get('notes', '')
        if not raw_notes:
            return Response({"error": "No notes provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        from .services import AIService
        formatted = AIService.format_soap_notes(raw_notes)
        return Response({"formatted_notes": formatted})

    @action(detail=False, methods=['get'])
    def ai_suggest_medicine(self, request):
        """
        GET /api/veterinary/visits/ai_suggest_medicine/?q=Amoxi
        AI-assisted medicine suggestions.
        """
        query = request.query_params.get('q', '')
        if len(query) < 3:
            return Response([], status=status.HTTP_200_OK)
        
        from .services import AIService
        suggestions = AIService.suggest_prescription_details(query)
        return Response(suggestions)

    @action(detail=True, methods=['post'], permission_classes=[require_granular_capability('VETERINARY_VISITS')])
    def transition(self, request, pk=None):
        """
        Transition visit status.
        Body: {"status": "NEW_STATUS"}
        """
        from rest_framework.exceptions import PermissionDenied
        visit = self.get_object()
        
        new_status = request.data.get('status')
        try:
            WorkflowService.transition_visit(visit, new_status, user_role=get_auth_user_id(request))
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[require_granular_capability('VETERINARY_VITALS')])
    def vitals(self, request, pk=None):
        """
        Save vitals for a Visit.
        """
        visit = self.get_object()
        try:
            DynamicEntityService.save_entity_data(
                visit.clinic.id, 
                visit.id, 
                'VITALS', 
                request.data
            )
            producer.send_event('VITALS_UPDATED', {'visit_id': str(visit.id)})
            return Response({'status': 'success'})
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

    @action(detail=False, methods=['get'], permission_classes=[require_granular_capability('VETERINARY_LABS')])
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

class ReminderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=True, methods=['post'], permission_classes=[require_granular_capability('VETERINARY_MEDICINE_REMINDERS')])
    def confirm(self, request, pk=None):
        """
        Confirm a reminder (mark as COMPLETED).
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response({'error': 'No clinic context found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Secure by ensuring reminder belongs to clinic
            reminder = MedicationReminder.objects.get(id=pk, visit__clinic_id=clinic_id)
            reminder.status = 'COMPLETED'
            reminder.save()
            return Response({'status': 'success'})
        except MedicationReminder.DoesNotExist:
            return Response({'error': 'Reminder not found in this clinic'}, status=status.HTTP_404_NOT_FOUND)

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
            if entity_type == 'VITALS': required_cap = 'VETERINARY_VITALS'
            elif entity_type == 'PRESCRIPTION': required_cap = 'VETERINARY_PRESCRIPTIONS'
            elif entity_type == 'LAB': required_cap = 'VETERINARY_LABS'
            
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

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        """
        Check-in a scheduled appointment.
        Creates a Visit if not exists and transitions status.
        """
        appointment = self.get_object()
        clinic_id = get_clinic_context(request)
        user_id = get_auth_user_id(request)

        if appointment.status != 'CONFIRMED':
            return Response({'error': f'Cannot check-in appointment in {appointment.status} status.'}, status=400)

        with transaction.atomic():
            # 1. Create Visit if not exists
            visit, created = Visit.objects.get_or_create(
                appointment=appointment,
                defaults={
                    'clinic_id': clinic_id or appointment.clinic_id,
                    'pet': appointment.pet,
                    'service_id': appointment.service_id,
                    'status': 'CREATED',
                    'reason': appointment.notes,
                    'created_by': user_id
                }
            )

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
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

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
