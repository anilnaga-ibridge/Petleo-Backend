
import uuid
from django.db import transaction
from django.utils import timezone
from .models import (
    DynamicFieldDefinition, DynamicFieldValue, Clinic, Visit,
    FormDefinition, FormField, FieldValidation, FormSubmission,
    PharmacyDispense, MedicationReminder, VeterinaryAuditLog
)
from .events import (
    emit_domain_event, VISIT_STATUS_CHANGED, LAB_RESULTS_READY, 
    PRESCRIPTION_FINALIZED, VISIT_COMPLETED
)

class DynamicEntityService:
    @staticmethod
    def get_entity_data(entity_id, entity_type=None):
        """
        Fetches all dynamic fields for a given entity_id.
        Returns a dictionary: {key: value}
        """
        queryset = DynamicFieldValue.objects.filter(entity_id=entity_id)
        if entity_type:
            queryset = queryset.filter(definition__entity_type=entity_type)
        
        data = {}
        for field_value in queryset:
            data[field_value.definition.key] = field_value.value
        return data

    @staticmethod
    def save_entity_data(clinic_id, entity_id, entity_type, data):
        """
        Saves dynamic fields for an entity.
        data: {key: value}
        """
        definitions = DynamicFieldDefinition.objects.filter(
            clinic_id=clinic_id, 
            entity_type=entity_type,
            is_active=True
        )
        definition_map = {d.key: d for d in definitions}
        
        saved_fields = []
        with transaction.atomic():
            for key, value in data.items():
                if key not in definition_map:
                    continue # Ignore unknown keys or raise error
                
                definition = definition_map[key]
                
                # Basic Validation
                if definition.is_required and value is None:
                    raise ValueError(f"Field '{definition.label}' is required.")
                
                # Create or Update
                obj, created = DynamicFieldValue.objects.update_or_create(
                    definition=definition,
                    entity_id=entity_id,
                    defaults={'value': value}
                )
                saved_fields.append(obj)
        
        return saved_fields

    @staticmethod
    def create_virtual_entity(clinic_id, entity_type, data):
        """
        Creates a 'virtual' entity (just a UUID + fields).
        Useful for Prescriptions, Lab Tests, etc.
        """
        entity_id = uuid.uuid4()
        DynamicEntityService.save_entity_data(clinic_id, entity_id, entity_type, data)
        DynamicEntityService.save_entity_data(clinic_id, entity_id, entity_type, data)
        return entity_id

class VisitQueueService:
    @staticmethod
    def get_queue(queue_name, clinic_id):
        """
        Returns a filtered QuerySet of visits based on the queue name.
        Strictly status-driven.
        """
        base_qs = Visit.objects.filter(clinic_id=clinic_id).select_related('pet', 'pet__owner')
        
        if queue_name == 'WAITING_ROOM':
            return base_qs.filter(status__in=['CREATED'])
        elif queue_name == 'VITALS_QUEUE':
            return base_qs.filter(status='CHECKED_IN')
        elif queue_name == 'DOCTOR_QUEUE':
            return base_qs.filter(status__in=['VITALS_RECORDED', 'LAB_RESULTS_READY'])
        elif queue_name == 'LAB_QUEUE':
            return base_qs.filter(status='LAB_ORDERED')
        elif queue_name == 'PHARMACY_QUEUE':
            return base_qs.filter(status='PRESCRIPTION_FINALIZED')
        elif queue_name == 'CLOSED':
            return base_qs.filter(status='CLOSED')
        else:
            return base_qs.none()

class WorkflowService:
    TRANSITIONS = {
        'CREATED': ['VITALS_RECORDED', 'CLOSED'],
        'VITALS_RECORDED': ['DOCTOR_ASSIGNED', 'CLOSED'],
        'DOCTOR_ASSIGNED': ['TESTS_ORDERED', 'PRESCRIPTION_FINALIZED', 'CLOSED'],
        'TESTS_ORDERED': ['LAB_RESULTS_READY', 'CLOSED'],
        'LAB_RESULTS_READY': ['PRESCRIPTION_FINALIZED', 'CLOSED'],
        'PRESCRIPTION_FINALIZED': ['MEDICINES_DISPENSED', 'FOLLOWUP_SCHEDULED', 'CLOSED'],
        'MEDICINES_DISPENSED': ['FOLLOWUP_SCHEDULED', 'CLOSED'],
        'FOLLOWUP_SCHEDULED': ['CLOSED'],
        'CLOSED': []
    }

    @staticmethod
    def transition_visit(visit, new_status, user_role=None):
        """
        Validates and executes a state transition.
        """
        current_status = visit.status
        allowed_next_states = WorkflowService.TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed_next_states:
            raise ValueError(f"Invalid transition from {current_status} to {new_status}")
        
        # TODO: Add Role-based validation here if needed
        # if new_status == 'DOCTOR_ASSIGNED' and user_role != 'RECEPTIONIST': ...

        # Capture Timestamps (SLA Tracking)
        now = timezone.now()
        if new_status == 'CHECKED_IN':
            visit.checked_in_at = now
        elif new_status == 'VITALS_RECORDED':
            visit.vitals_completed_at = now
        # For vitals_started_at, we might need a separate trigger, but for now let's assume it starts when checked in? 
        # Or maybe we need a 'VITALS_STARTED' status? Spec says "vitals_started_at".
        # Let's set vitals_started_at when it enters VITALS_QUEUE (which is CHECKED_IN).
            visit.vitals_started_at = visit.checked_in_at # Approximation if not explicit
            
        elif new_status == 'DOCTOR_ASSIGNED': # Or when doctor actually starts? For now, this is a proxy.
            visit.doctor_started_at = now
        elif new_status == 'LAB_ORDERED':
            visit.lab_ordered_at = now
        elif new_status == 'LAB_RESULTS_READY':
            visit.lab_completed_at = now
        elif new_status == 'PRESCRIPTION_FINALIZED':
            visit.prescription_finalized_at = now
        elif new_status == 'MEDICINES_DISPENSED':
            visit.pharmacy_completed_at = now
        elif new_status == 'CLOSED':
            visit.closed_at = now
        
        visit.status = new_status
        visit.save()
        return visit

        visit.status = new_status
        visit.save()

        # Emit Events
        emit_domain_event(VISIT_STATUS_CHANGED, visit, {'new_status': new_status})
        
        if new_status == 'LAB_RESULTS_READY':
            emit_domain_event(LAB_RESULTS_READY, visit)
        elif new_status == 'PRESCRIPTION_FINALIZED':
            emit_domain_event(PRESCRIPTION_FINALIZED, visit)
        elif new_status == 'CLOSED':
            emit_domain_event(VISIT_COMPLETED, visit)

        # Audit Log
        if user_role: # Or user_id if we pass it
             VeterinaryAuditLog.objects.create(
                visit=visit,
                action_type='STATUS_CHANGE',
                performed_by=str(user_role), # Should be user ID ideally
                metadata={'old_status': current_status, 'new_status': new_status}
            )
            
        return visit

class MetadataService:
    @staticmethod
    def create_form_definition(data):
        """
        Creates a new form definition with fields.
        data: {
            "code": "VITALS",
            "name": "Vitals Form",
            "fields": [...]
        }
        """
        fields_data = data.pop('fields', [])
        with transaction.atomic():
            form = FormDefinition.objects.create(**data)
            
            for field_data in fields_data:
                validations_data = field_data.pop('validations', [])
                field = FormField.objects.create(form_definition=form, **field_data)
                
                for val_data in validations_data:
                    FieldValidation.objects.create(form_field=field, **val_data)
                    
        return form

    @staticmethod
    def submit_form(visit_id, form_code, data, user_id):
        """
        Submits data for a specific form in a visit.
        """
        try:
            form_def = FormDefinition.objects.get(code=form_code, is_active=True)
        except FormDefinition.DoesNotExist:
            raise ValueError(f"Form {form_code} not found or inactive.")
            
        # TODO: Validate data against FormField definitions and FieldValidation rules
        # For Phase 2, we assume frontend sends valid data, but backend validation is critical for prod.
        
        submission = FormSubmission.objects.create(
            form_definition=form_def,
            visit_id=visit_id,
            submitted_by=user_id,
            data=data
        )
        return submission

    @staticmethod
    def get_visit_summary(visit_id):
        """
        Returns a summary of the visit including all form submissions.
        """
        visit = Visit.objects.select_related('pet', 'pet__owner', 'clinic').get(id=visit_id)
        submissions = FormSubmission.objects.filter(visit=visit).select_related('form_definition')
        
        summary = {
            "visit": {
                "id": visit.id,
                "status": visit.status,
                "created_at": visit.created_at,
                "type": visit.visit_type
            },
            "pet": {
                "id": visit.pet.id,
                "name": visit.pet.name,
                "species": visit.pet.species,
                "breed": visit.pet.breed,
            },
            "owner": {
                "id": visit.pet.owner.id,
                "name": visit.pet.owner.name,
                "phone": visit.pet.owner.phone,
                "email": visit.pet.owner.email,
                "address": visit.pet.owner.address,
            },
            "forms": {}
        }
        
        for sub in submissions:
            code = sub.form_definition.code
            if code not in summary["forms"]:
                summary["forms"][code] = []
            summary["forms"][code].append({
                "id": sub.id,
                "data": sub.data,
                "submitted_at": sub.created_at,
                "submitted_by": sub.submitted_by
            })
            
            
        return summary

# ========================
# PHASE 3: EXECUTION SERVICES
# ========================

class LabService:
    @staticmethod
    def get_pending_lab_orders(clinic_id):
        """
        Returns all visits with pending lab orders.
        """
        # Find submissions for LAB_ORDER form where no corresponding LAB_RESULTS submission exists
        # This is a simplified logic. In prod, we might link them explicitly.
        lab_form = FormDefinition.objects.filter(code='LAB_ORDER').first()
        if not lab_form:
            return []
            
        submissions = FormSubmission.objects.filter(
            form_definition=lab_form,
            visit__clinic_id=clinic_id
        ).select_related('visit', 'visit__pet', 'visit__pet__owner')
        
        pending = []
        for sub in submissions:
            # Check if results exist
            # Assuming we link results to order via some metadata or just check if visit has results
            # For Phase 3, let's just return all orders for visits not in 'CLOSED' state
            if sub.visit.status != 'CLOSED':
                pending.append({
                    "visit_id": sub.visit.id,
                    "pet_name": sub.visit.pet.name,
                    "owner_name": sub.visit.pet.owner.name,
                    "order_date": sub.created_at,
                    "order_details": sub.data
                })
        return pending

class PharmacyService:
    @staticmethod
    def get_pending_prescriptions(clinic_id):
        """
        Returns visits with prescriptions that haven't been fully dispensed.
        """
        presc_form = FormDefinition.objects.filter(code='PRESCRIPTION').first()
        if not presc_form:
            return []
            
        submissions = FormSubmission.objects.filter(
            form_definition=presc_form,
            visit__clinic_id=clinic_id
        ).exclude(dispenses__status='DISPENSED').select_related('visit', 'visit__pet')
        
        return submissions

    @staticmethod
    def dispense_medicines(submission_id, user_id):
        """
        Marks a prescription as dispensed and triggers reminders.
        """
        submission = FormSubmission.objects.get(id=submission_id)
        
        with transaction.atomic():
            dispense = PharmacyDispense.objects.create(
                visit=submission.visit,
                prescription_submission=submission,
                dispensed_by=user_id,
                status='DISPENSED'
            )
            
            # Trigger Reminder Generation
            ReminderService.generate_reminders(submission.visit.id, submission.data)
            
        return dispense

class ReminderService:
    @staticmethod
    def generate_reminders(visit_id, prescription_data):
        """
        Generates reminders based on prescription data.
        prescription_data: { "medicines": [ { "name": "X", "frequency": "1-0-1", "days": 5 } ] }
        """
        visit = Visit.objects.get(id=visit_id)
        medicines = prescription_data.get('medicines', [])
        
        reminders = []
        for med in medicines:
            # Parse frequency and duration to calculate schedule
            # Simplified for Phase 3: Create one active reminder record per medicine
            reminder = MedicationReminder.objects.create(
                visit=visit,
                pet=visit.pet,
                medicine_name=med.get('name', 'Unknown'),
                dosage=med.get('dosage', 'As prescribed'),
                frequency=med.get('frequency', 'Daily'),
                start_date=visit.created_at.date(),
                end_date=visit.created_at.date(), # Should calculate based on duration
                next_reminder_at=visit.created_at # Should be calculated
            )
            reminders.append(reminder)
            
        return reminders

class VisitTimelineService:
    @staticmethod
    def get_timeline(visit_id):
        """
        Returns the timeline of a visit.
        """
        visit = Visit.objects.get(id=visit_id)
        return {
            "created_at": visit.created_at,
            "checked_in_at": visit.checked_in_at,
            "vitals_started_at": visit.vitals_started_at,
            "vitals_completed_at": visit.vitals_completed_at,
            "doctor_started_at": visit.doctor_started_at,
            "lab_ordered_at": visit.lab_ordered_at,
            "lab_completed_at": visit.lab_completed_at,
            "prescription_finalized_at": visit.prescription_finalized_at,
            "pharmacy_completed_at": visit.pharmacy_completed_at,
            "closed_at": visit.closed_at,
            "status": visit.status
        }

class ClinicAnalyticsService:
    @staticmethod
    def get_dashboard_metrics(clinic_id):
        """
        Returns real-time analytics for the clinic dashboard.
        """
        today = timezone.now().date()
        visits_today = Visit.objects.filter(clinic_id=clinic_id, created_at__date=today)
        
        # 1. Visits Today
        total_visits = visits_today.count()
        
        # 2. Avg Wait Time (Created -> Doctor Started)
        # This is a simplification. Real wait time might be Check-in -> Doctor.
        # Let's use Created -> Doctor for now as we don't have explicit Check-in timestamp yet.
        completed_visits = visits_today.filter(doctor_started_at__isnull=False)
        avg_wait_minutes = 0
        if completed_visits.exists():
            total_wait = sum([(v.doctor_started_at - v.created_at).total_seconds() for v in completed_visits])
            avg_wait_minutes = int((total_wait / completed_visits.count()) / 60)
            
        # 3. Visits by Status
        status_counts = {}
        for status, _ in Visit.STATUS_CHOICES:
            status_counts[status] = visits_today.filter(status=status).count()
            
        return {
            "visits_today": total_visits,
            "avg_wait_time_minutes": avg_wait_minutes,
            "status_breakdown": status_counts
        }
