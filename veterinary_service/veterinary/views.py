
def get_clinic_context(request):
    """
    Robustly resolve clinic_id from request.
    1. Checks if already attached to request.user (via Middleware/Auth)
    2. Checks request headers (X-Clinic-ID) or query params as a backup.
    STRICT: No auto-guessing for Multi-Clinic Organizations.
    """
    clinic_id = getattr(request.user, 'clinic_id', None)
    if not clinic_id:
        clinic_id = request.headers.get('X-Clinic-ID') or request.GET.get('clinic_id')
    return clinic_id
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import (
    Clinic, PetOwner, Pet, Visit,
    DynamicFieldDefinition, DynamicFieldValue,
    FormDefinition, FormField, FormSubmission,
    LabTestTemplate, LabTestField, LabOrder, LabResult
)
from .serializers import (
    ClinicSerializer, PetOwnerSerializer, PetSerializer, VisitSerializer,
    DynamicFieldDefinitionSerializer, DynamicFieldValueSerializer,
    DynamicEntitySerializer,
    FormDefinitionSerializer, FormSubmissionSerializer, VisitDetailSerializer,
    LabTestTemplateSerializer, LabOrderSerializer, LabResultSerializer, PharmacyDispenseSerializer
)
from .services import (
    DynamicEntityService, WorkflowService, MetadataService, 
    LabService, PharmacyService, ReminderService, VisitQueueService,
    VisitTimelineService, ClinicAnalyticsService
)
from .kafka.producer import producer
from .permissions import HasVeterinaryAccess, IsClinicStaffOfPet, require_capability
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
                        defaults={'name': owner_name or "New Owner"}
                    )
                    log_trace(f"SAVING WITH NEW/FOUND OWNER: {owner.id} (Created: {created})")
                    serializer.save(owner=owner)
                    return
                else:
                    log_trace("ERROR: owner_phone missing in payload.")
                    raise ValidationError({"owner_phone": "Owner phone is required for registration."})

            log_trace(f"SAVING WITH PROVIDED OWNER_ID: {owner_id}")
            serializer.save()
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

class VisitQueueViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'], url_path='(?P<queue_name>[^/.]+)')
    def get_queue(self, request, queue_name=None):
        """
        GET /veterinary/visits/queues/{queue_name}
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response({'error': 'No active clinic context found'}, status=status.HTTP_400_BAD_REQUEST)
             
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
            # [FIX] Allow Organization/Provider Admins to access ALL queues
            role = str(getattr(request.user, 'role', '')).upper()
            if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER']:
                pass # Bypass check
            else:
                user_perms = getattr(request.user, 'permissions', [])
                if required_cap not in user_perms:
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
        GET /veterinary/analytics/dashboard?date=YYYY-MM-DD
        """
        clinic_id = get_clinic_context(request)
        if not clinic_id:
             return Response({'error': 'No active clinic context found'}, status=status.HTTP_400_BAD_REQUEST)
             
        date_param = request.query_params.get('date')
        metrics = ClinicAnalyticsService.get_dashboard_metrics(clinic_id, date_param)
        return Response(metrics)

class VisitViewSet(viewsets.ModelViewSet):
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def get_queryset(self):
        clinic_id = get_clinic_context(self.request)
        
        if clinic_id:
            return Visit.objects.filter(clinic_id=clinic_id)
        return Visit.objects.none()

    def perform_create(self, serializer):
        # [SENIOR DEV FIX] Auto-resolve clinic if missing from frontend
        clinic_id = get_clinic_context(self.request)
        
        if not serializer.validated_data.get('clinic') and clinic_id:
            instance = serializer.save(clinic_id=clinic_id)
        else:
            instance = serializer.save()

        producer.send_event('VET_VISIT_CREATED', {
            'visit_id': str(instance.id),
            'pet_id': str(instance.pet.id),
            'clinic_id': str(instance.clinic.id),
            'status': instance.status
        })

    def perform_update(self, serializer):
        # [SENIOR DEV FIX] Handle status transitions via standard update/patch
        visit = self.get_object()
        old_status = visit.status
        new_status = serializer.validated_data.get('status')

        if new_status and new_status != old_status:
            try:
                # Use WorkflowService to handle validation and side effects (timestamps, etc.)
                WorkflowService.transition_visit(visit, new_status)
                # Remove status from validated_data so serializer doesn't re-save it
                serializer.validated_data.pop('status')
            except ValueError as e:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"status": str(e)})

        serializer.save()

    @action(detail=True, methods=['post'], url_path='check-in')
    @require_capability('VETERINARY_VISITS')
    def check_in(self, request, pk=None):
        visit = self.get_object()
        try:
            WorkflowService.transition_visit(visit, 'CHECKED_IN')
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @require_capability(['VETERINARY_VISITS', 'VETERINARY_DOCTOR']) # Basic capability, specific transitions might need more
    def transition(self, request, pk=None):
        """
        Transition visit status.
        Body: {"status": "NEW_STATUS"}
        """
        visit = self.get_object()
        new_status = request.data.get('status')
        try:
            WorkflowService.transition_visit(visit, new_status)
            return Response({'status': 'success', 'new_status': visit.status})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @require_capability('VETERINARY_VITALS')
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
                request.user.id # Assuming user ID is available
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
        # In a real app, we'd link request.user.id to PetOwner.auth_user_id
        return Visit.objects.filter(pet__owner__auth_user_id=self.request.user.id).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def pets(self, request):
        """
        GET /veterinary/pet-owner/pets
        """
        pets = Pet.objects.filter(owner__auth_user_id=request.user.id)
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
            visit = Visit.objects.get(id=visit_id, pet__owner__auth_user_id=request.user.id)
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
            form_definition__code='PRESCRIPTION_FORM'
        )
        return Response(FormSubmissionSerializer(submissions, many=True).data)

class FormDefinitionViewSet(viewsets.ModelViewSet):
    queryset = FormDefinition.objects.all()
    serializer_class = FormDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]
    lookup_field = 'code'

# ========================
# PHASE 3: EXECUTION VIEWSETS
# ========================

class LabViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'])
    @require_capability('VETERINARY_LABS')
    def pending(self, request):
        """
        List pending lab orders for the clinic.
        """
        # Assuming clinic_id is available in user context or request
        # For Phase 3, we'll extract it from the user's profile or request params
        clinic_id = getattr(request.user, 'clinic_id', None)
        if not clinic_id:
             return Response({'error': 'No active clinic context found'}, status=status.HTTP_400_BAD_REQUEST)
             
        orders = LabService.get_pending_lab_orders(clinic_id)
        return Response(orders)

class PharmacyViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'])
    @require_capability('VETERINARY_MEDICINE_REMINDERS')
    def pending(self, request):
        """
        List pending prescriptions.
        """
        clinic_id = getattr(request.user, 'clinic_id', None)
        if not clinic_id:
             return Response({'error': 'No active clinic context found'}, status=status.HTTP_400_BAD_REQUEST)
             
        submissions = PharmacyService.get_pending_prescriptions(clinic_id)
        return Response(FormSubmissionSerializer(submissions, many=True).data)

    @action(detail=False, methods=['post'])
    @require_capability('VETERINARY_MEDICINE_REMINDERS') # Pharmacy capability
    def dispense(self, request):
        """
        Dispense medicines for a prescription submission.
        Body: { "submission_id": "UUID" }
        """
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({'error': 'submission_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            dispense = PharmacyService.dispense_medicines(submission_id, request.user.id)
            return Response(PharmacyDispenseSerializer(dispense).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReminderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirm a reminder (mark as COMPLETED).
        """
        try:
            reminder = MedicationReminder.objects.get(id=pk)
            reminder.status = 'COMPLETED'
            reminder.save()
            return Response({'status': 'success'})
        except MedicationReminder.DoesNotExist:
            return Response({'error': 'Reminder not found'}, status=status.HTTP_404_NOT_FOUND)

class DynamicFieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = DynamicFieldDefinition.objects.all()
    serializer_class = DynamicFieldDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

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
        # 1. Ensure user is an Organization/Owner
        user = self.request.user
        role = str(getattr(user, 'role', '')).upper()
        
        # Org/Owner Only
        if role not in ['ORGANIZATION', 'INDIVIDUAL', 'ORGANIZATION_PROVIDER', 'PROVIDER']:
             return self.queryset.none()
             
        # Filter by org_id (which is the user's ID for Orgs/Individuals)
        org_id = str(user.id)
        if hasattr(self.request.auth, 'get'):
             org_id = self.request.auth.get('user_id') or org_id
             
        qs = self.queryset.filter(clinic__organization_id=org_id)
        
        # Optional: Filter by specific staff member
        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            qs = qs.filter(staff__auth_user_id=staff_id)
            
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        org_id = str(user.id)
        if hasattr(self.request.auth, 'get'):
             org_id = self.request.auth.get('user_id') or org_id
             
        # Validate that the clinic belongs to this organization
        clinic = serializer.validated_data.get('clinic')
        if str(clinic.organization_id) != org_id:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("You can only assign staff to your own clinics.")
             
        # Check if staff object exists properly
        staff = serializer.validated_data.get('staff')
        # If staff doesn't exist in VeterinaryStaff yet, we might need to auto-create it?
        # Assuming staff exists because FE will likely pick from existing list.
             
        serializer.save()
