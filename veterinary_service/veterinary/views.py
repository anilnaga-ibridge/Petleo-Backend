
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import (
    Clinic, PetOwner, Pet, Visit, 
    Clinic, PetOwner, Pet, Visit, 
    DynamicFieldDefinition, DynamicFieldValue,
    FormDefinition, FormField, FormSubmission,
    PharmacyDispense, MedicationReminder
)
from .serializers import (
    ClinicSerializer, PetOwnerSerializer, PetSerializer, VisitSerializer, 
    DynamicFieldDefinitionSerializer, DynamicFieldValueSerializer,
    DynamicEntitySerializer,
    FormDefinitionSerializer, FormSubmissionSerializer, VisitDetailSerializer,
    PharmacyDispenseSerializer, MedicationReminderSerializer
)
from .services import (
    DynamicEntityService, WorkflowService, MetadataService, 
    LabService, PharmacyService, ReminderService, VisitQueueService,
    VisitTimelineService, ClinicAnalyticsService
)
from .kafka.producer import producer
from .permissions import HasVeterinaryAccess, require_capability
from .monetization import feature_tier, PRO, ENTERPRISE

class ClinicViewSet(viewsets.ModelViewSet):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

class PetOwnerViewSet(viewsets.ModelViewSet):
    queryset = PetOwner.objects.all()
    serializer_class = PetOwnerSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

class PetViewSet(viewsets.ModelViewSet):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

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
        clinic_id = request.query_params.get('clinic_id') # Should extract from user context
        if not clinic_id:
             return Response({'error': 'clinic_id required'}, status=status.HTTP_400_BAD_REQUEST)
             
        # Map queue name to required capability
        REQUIRED_CAPS = {
            'WAITING_ROOM': 'VETERINARY_VISITS',
            'VITALS_QUEUE': 'VETERINARY_VITALS',
            'DOCTOR_QUEUE': 'VETERINARY_PRESCRIPTIONS',
            'LAB_QUEUE': 'VETERINARY_LABS',
            'PHARMACY_QUEUE': 'VETERINARY_MEDICINE_REMINDERS'
        }
        
        required_cap = REQUIRED_CAPS.get(queue_name)
        if required_cap:
            # Manual check because it's dynamic
            user_perms = getattr(request.user, 'permissions', [])
            if required_cap not in user_perms:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        queryset = VisitQueueService.get_queue(queue_name, clinic_id)
        return Response(VisitSerializer(queryset, many=True).data)

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    @action(detail=False, methods=['get'])
    @feature_tier(PRO)
    def dashboard(self, request):
        """
        GET /veterinary/analytics/dashboard
        """
        clinic_id = request.query_params.get('clinic_id')
        if not clinic_id:
             return Response({'error': 'clinic_id required'}, status=status.HTTP_400_BAD_REQUEST)
             
        metrics = ClinicAnalyticsService.get_dashboard_metrics(clinic_id)
        return Response(metrics)

class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated, HasVeterinaryAccess]

    def perform_create(self, serializer):
        instance = serializer.save()
        producer.send_event('VET_VISIT_CREATED', {
            'visit_id': str(instance.id),
            'pet_id': str(instance.pet.id),
            'clinic_id': str(instance.clinic.id),
            'status': instance.status
        })

    @action(detail=True, methods=['post'])
    @require_capability('VETERINARY_VISITS') # Basic capability, specific transitions might need more
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
    permission_classes = [permissions.IsAuthenticated] # Add IsPetOwner custom permission later
    serializer_class = VisitSerializer

    def get_queryset(self):
        # Filter visits where the pet belongs to the logged-in user
        # Assuming request.user.id matches Owner ID in Pet Service (or linked via Auth)
        # For Phase 4, we assume request.user.id is the owner_id
        user_id = self.request.user.id # Or usage of a specific claim
        # We need to filter Visits where Visit.pet.owner.id == user_id
        # Since Owner is a virtual entity or linked model, we might need to adjust.
        # If Pet.owner is a foreign key to a User/Owner model:
        return Visit.objects.filter(pet__owner__id=user_id).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def prescriptions(self, request):
        """
        GET /veterinary/pet-owner/prescriptions
        """
        user_id = self.request.user.id
        # Logic to fetch prescriptions for this owner
        # This requires traversing Visit -> FormSubmission(Prescription) -> Pet -> Owner
        # Simplified for now:
        return Response([])

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
        clinic_id = request.query_params.get('clinic_id') 
        if not clinic_id:
             return Response({'error': 'clinic_id required'}, status=status.HTTP_400_BAD_REQUEST)
             
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
        clinic_id = request.query_params.get('clinic_id')
        if not clinic_id:
             return Response({'error': 'clinic_id required'}, status=status.HTTP_400_BAD_REQUEST)
             
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
        clinic_id = request.data.get('clinic_id') # Should come from context/user normally

        if not clinic_id:
             return Response({'error': 'clinic_id required'}, status=status.HTTP_400_BAD_REQUEST)

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
