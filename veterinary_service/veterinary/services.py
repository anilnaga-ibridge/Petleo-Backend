import uuid
import json
import urllib.request
import urllib.error
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField
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
    def get_queue(queue_name, clinic_id, date_filter=None):
        """
        Returns a filtered QuerySet of visits based on the queue name.
        Strictly status-driven.
        """
        base_qs = Visit.objects.filter(clinic_id=clinic_id).select_related('pet', 'pet__owner').order_by('created_at')
        
        if queue_name == 'WAITING_ROOM':
            return base_qs.filter(status__in=['CREATED'])
            
        elif queue_name == 'VITALS_QUEUE':
            from django.utils import timezone
            import datetime
            target_date = timezone.now()
            if date_filter:
                try:
                    target_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d')
                except ValueError: pass
            
            return base_qs.filter(
                status__in=['CHECKED_IN', 'VITALS_RECORDED'],
                created_at__year=target_date.year,
                created_at__month=target_date.month,
                created_at__day=target_date.day
            )
            
        elif queue_name == 'DOCTOR_QUEUE':
            # Rule 1: Show ALL visits for the selected date (default Today)
            from django.utils import timezone
            import datetime
            target_date = timezone.now()
            if date_filter:
                try:
                    target_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d')
                except ValueError: pass

            # Rule 2: Persistence - Include finalized/completed too if it matches date
            # Rule 4: Sorting
            qs = base_qs.filter(
                status__in=[
                    'VITALS_RECORDED', 'DOCTOR_ASSIGNED', 'LAB_COMPLETED', 
                    'PRESCRIPTION_FINALIZED', 'LAB_REQUESTED', 
                    'TREATMENT_COMPLETED', 'CHECKED_IN', 'MEDICINES_DISPENSED'
                ],
                created_at__year=target_date.year,
                created_at__month=target_date.month,
                created_at__day=target_date.day
            ).annotate(
                sort_order=Case(
                    When(status='VITALS_RECORDED', then=Value(1)),
                    When(status='DOCTOR_ASSIGNED', then=Value(2)),
                    When(status='LAB_COMPLETED', then=Value(3)),
                    When(status='PRESCRIPTION_FINALIZED', then=Value(4)),
                    When(status='CHECKED_IN', then=Value(5)), # Waiting for Vitals
                    default=Value(10),
                    output_field=IntegerField(),
                )
            ).order_by('sort_order', 'created_at')
            return qs

        elif queue_name == 'LAB_QUEUE':
            return base_qs.filter(status='LAB_REQUESTED')
        elif queue_name == 'PHARMACY_QUEUE':
            # [FIX] Include any visit with a pending prescription, regardless of status (e.g. LAB_REQUESTED)
            # This ensures patients doing Labs after Prescriptions don't disappear from Pharmacy.
            pending_visit_ids = FormSubmission.objects.filter(
                form_definition__code='PRESCRIPTION',
                visit__clinic_id=clinic_id
            ).exclude(
                dispenses__status='DISPENSED'
            ).values_list('visit_id', flat=True)
            
            return base_qs.filter(id__in=pending_visit_ids).exclude(status='CLOSED').distinct()
        elif queue_name == 'NURSE_QUEUE':
            return base_qs.filter(status='MEDICINES_DISPENSED')
        elif queue_name == 'CLOSED':
            return base_qs.filter(status='TREATMENT_COMPLETED')
        else:
            return base_qs.none()

class WorkflowService:
    TRANSITIONS = {
        'CREATED': ['CHECKED_IN', 'VITALS_RECORDED', 'CLOSED'],
        'CHECKED_IN': ['VITALS_RECORDED', 'CLOSED'],
        'VITALS_RECORDED': ['DOCTOR_ASSIGNED', 'CLOSED'],
        'DOCTOR_ASSIGNED': ['LAB_REQUESTED', 'PRESCRIPTION_FINALIZED', 'CLOSED'],
        'LAB_REQUESTED': ['LAB_COMPLETED', 'CLOSED', 'PRESCRIPTION_FINALIZED', 'MEDICINES_DISPENSED'], # Allow partial dispense during labs
        'LAB_COMPLETED': ['PRESCRIPTION_FINALIZED', 'CLOSED', 'MEDICINES_DISPENSED'],
        'PRESCRIPTION_FINALIZED': ['MEDICINES_DISPENSED', 'FOLLOWUP_SCHEDULED', 'CLOSED', 'LAB_REQUESTED'],
        'MEDICINES_DISPENSED': ['TREATMENT_COMPLETED', 'CLOSED', 'LAB_REQUESTED'], # Allow labs after meds
        'TREATMENT_COMPLETED': ['CLOSED'],
        'CLOSED': []
    }

    @staticmethod
    def transition_visit(visit, new_status, user_role=None):
        """
        Validates and executes a state transition.
        """
        current_status = visit.status
        
        # IDEMPOTENCY CHECK: If already in target state, do nothing
        if current_status == new_status:
            return visit

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
        elif new_status == 'LAB_REQUESTED':
            visit.lab_ordered_at = now
        elif new_status == 'LAB_COMPLETED':
            visit.lab_completed_at = now
        elif new_status == 'PRESCRIPTION_FINALIZED':
            visit.prescription_finalized_at = now
        elif new_status == 'MEDICINES_DISPENSED':
            visit.pharmacy_completed_at = now
        elif new_status == 'TREATMENT_COMPLETED':
            visit.closed_at = now
        
        visit.status = new_status
        visit.save()

        # Emit Events
        emit_domain_event(VISIT_STATUS_CHANGED, visit, {'new_status': new_status})
        
        if new_status == 'LAB_COMPLETED':
            emit_domain_event(LAB_RESULTS_READY, visit)
        elif new_status == 'PRESCRIPTION_FINALIZED':
            emit_domain_event(PRESCRIPTION_FINALIZED, visit)
        elif new_status == 'TREATMENT_COMPLETED':
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

        # Add Audit Log for tracking
        action_map = {
            'VITALS': 'VITALS_ENTERED',
            'PRESCRIPTION': 'PRESCRIPTION_CREATED',
            'LAB_ORDER': 'LAB_ORDERED',
            'LAB_RESULTS': 'LAB_RESULT_ADDED'
        }
        action_type = action_map.get(form_code, 'FORM_SUBMITTED')
        
        from .models import VeterinaryAuditLog
        VeterinaryAuditLog.objects.create(
            visit_id=visit_id,
            action_type=action_type,
            performed_by=str(user_id)
        )

        return submission

    @staticmethod
    def get_visit_summary(visit_id):
        """
        Returns a summary of the visit including all form submissions.
        """
        visit = Visit.objects.select_related('pet', 'pet__owner', 'clinic').get(id=visit_id)
        submissions = FormSubmission.objects.filter(visit=visit).select_related('form_definition')
        
        # Reconcile vitals: Latest form submission first (New Engine), then legacy dynamic data
        last_sub = submissions.filter(form_definition__code='VITALS').order_by('-created_at').first()
        
        if last_sub:
            vitals = last_sub.data
        else:
            vitals = DynamicEntityService.get_entity_data(visit_id, 'VITALS')

        # Get latest Lab Order, Results and Prescription
        lab_order = submissions.filter(form_definition__code='LAB_ORDER').order_by('-created_at').first()
        lab_results = submissions.filter(form_definition__code='LAB_RESULTS').order_by('-created_at').first()
        prescription = submissions.filter(form_definition__code='PRESCRIPTION').order_by('-created_at').first()

        from .serializers import PetSerializer, PetOwnerSerializer

        summary = {
            "id": str(visit.id),
            "status": visit.status,
            "visit_type": visit.visit_type,
            "reason": visit.reason,
            "created_at": visit.created_at,
            "vitals": vitals,
            "lab_order": lab_order.data if lab_order else {},
            "lab_results": lab_results.data if lab_results else {},
            "prescription": prescription.data if prescription else {},
            "pet": PetSerializer(visit.pet).data,
            "owner": PetOwnerSerializer(visit.pet.owner).data if visit.pet.owner else None,
            "doctor_assigned": "Dr. Smith",
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
    def _get_trend(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return int(((current - previous) / previous) * 100)

    @staticmethod
    def get_reception_metrics(clinic_id, date_obj):
        """
        Reception Analytics:
        - Visits Created Today vs Yesterday
        - Current Queue Status
        """
        import datetime
        yesterday = date_obj - datetime.timedelta(days=1)
        
        # 1. Total Visits (Arrivals)
        today_visits = Visit.objects.filter(clinic_id=clinic_id, created_at__date=date_obj).count()
        yesterday_visits = Visit.objects.filter(clinic_id=clinic_id, created_at__date=yesterday).count()
        
        # 2. Pipeline Status
        # "Pending" for reception = CREATED (Waiting for check-in)
        pending_checkin = Visit.objects.filter(clinic_id=clinic_id, status='CREATED', created_at__date=date_obj).count()
        # "Checked In" = Passed reception, waiting for vitals
        checked_in = Visit.objects.filter(clinic_id=clinic_id, status='CHECKED_IN', created_at__date=date_obj).count()
        
        # 3. No Shows / Cancelled (using CLOSED status + reason or just CLOSED for now if no specific flag)
        # Assuming CLOSED at CREATED stage implies cancellation
        cancelled = Visit.objects.filter(clinic_id=clinic_id, status='CLOSED', created_at__date=date_obj).count()

        return {
            "today_visits": today_visits,
            "yesterday_visits": yesterday_visits,
            "trend": ClinicAnalyticsService._get_trend(today_visits, yesterday_visits),
            "checked_in": checked_in,
            "pending": pending_checkin,
            "cancelled": cancelled
        }

    @staticmethod
    def get_vitals_metrics(clinic_id, date_obj):
        """
        Vitals Analytics:
        - Patients Received (Passed Check-in)
        - Vitals Completed (Recorded)
        - Pending (Waiting in Vitals Queue)
        """
        # Patients Received: Anyone who reached CHECKED_IN or beyond today
        # We use checked_in_at timestamp for accuracy if available, else created_at
        patients_received = Visit.objects.filter(
            clinic_id=clinic_id, 
            checked_in_at__date=date_obj
        ).count()

        # Vitals Completed: Anyone who reached VITALS_RECORDED today
        vitals_completed = Visit.objects.filter(
            clinic_id=clinic_id,
            vitals_completed_at__date=date_obj
        ).count()

        # Pending: Currently CHECKED_IN (Waiting for Vitals)
        pending_vitals = Visit.objects.filter(
            clinic_id=clinic_id, 
            status='CHECKED_IN'
        ).count()

        # Avg Time per Patient (Check In -> Vitals Recorded)
        # We calculate for visits completed TODAY
        completed_today_instances = Visit.objects.filter(
            clinic_id=clinic_id,
            vitals_completed_at__date=date_obj,
            checked_in_at__isnull=False
        )
        
        avg_time = 0
        if completed_today_instances.exists():
            total_seconds = sum(
                (v.vitals_completed_at - v.checked_in_at).total_seconds() 
                for v in completed_today_instances
            )
            avg_time = int((total_seconds / completed_today_instances.count()) / 60) # Minutes

        return {
            "patients_received": patients_received,
            "vitals_completed": vitals_completed,
            "pending_vitals": pending_vitals,
            "avg_time_minutes": avg_time
        }

    @staticmethod
    def get_doctor_metrics(clinic_id, date_obj):
        """
        Doctor Analytics:
        - Breakdown by Doctor (derived from user_id in logs/assignments)
        """
        # Since we don't have a hard 'doctor_id' on Visit, we infer activity.
        # Use VeterinaryAuditLog or FormSubmissions to group by doctor?
        # For this phase, we will return aggregate numbers and a dummy list 
        # as the 'doctor' attribution requires deeper schema changes or AuditLog queries which can be slow.
        
        # 1. Patients Seen (Doctor Assigned -> Prescription/Lab)
        # Count visits where doctor_started_at is today
        patients_seen = Visit.objects.filter(clinic_id=clinic_id, doctor_started_at__date=date_obj).count()
        
        # 2. Prescriptions Written Today
        prescriptions = FormSubmission.objects.filter(
            visit__clinic_id=clinic_id,
            form_definition__code='PRESCRIPTION',
            created_at__date=date_obj
        ).count()

        # 3. Lab Tests Ordered Today
        lab_orders = FormSubmission.objects.filter(
            visit__clinic_id=clinic_id,
            form_definition__code='LAB_ORDER',
            created_at__date=date_obj
        ).count()
        
        # 4. Lab Reports Reviewed (using LAB_COMPLETED status timestamp)
        lab_reviews = Visit.objects.filter(
            clinic_id=clinic_id,
            lab_completed_at__date=date_obj
        ).count()
        
        # 5. Pending (Waiting for Doctor)
        # Visits in VITALS_RECORDED (Ready for doctor) or DOCTOR_ASSIGNED (In progress)
        pending_doctor = Visit.objects.filter(
            clinic_id=clinic_id,
            status__in=['VITALS_RECORDED', 'DOCTOR_ASSIGNED']
        ).count()

        return {
            "patients_seen": patients_seen,
            "prescriptions_written": prescriptions,
            "lab_tests_ordered": lab_orders,
            "lab_reports_reviewed": lab_reviews,
            "pending_patients": pending_doctor
        }

    @staticmethod
    def get_lab_metrics(clinic_id, date_obj):
        requests_received = Visit.objects.filter(clinic_id=clinic_id, lab_ordered_at__date=date_obj).count()
        reports_completed = Visit.objects.filter(clinic_id=clinic_id, lab_completed_at__date=date_obj).count()
        
        # Pending: Currently LAB_REQUESTED
        pending_labs = Visit.objects.filter(clinic_id=clinic_id, status='LAB_REQUESTED').count()
        
        # Avg Turnaround (Ordered -> Completed)
        completed_today = Visit.objects.filter(
            clinic_id=clinic_id,
            lab_completed_at__date=date_obj,
            lab_ordered_at__isnull=False
        )
        avg_time = 0
        if completed_today.exists():
            total_seconds = sum(
                (v.lab_completed_at - v.lab_ordered_at).total_seconds()
                for v in completed_today
            )
            avg_time = int((total_seconds / completed_today.count()) / 60)

        return {
            "lab_requests_received": requests_received,
            "samples_collected": requests_received, # Assuming sample collected same as request for now
            "reports_completed": reports_completed,
            "pending_labs": pending_labs,
            "avg_turnaround_minutes": avg_time
        }

    @staticmethod
    def get_pharmacy_metrics(clinic_id, date_obj):
        # Pharmacy is driven by Prescriptions and Dispenses
        
        # 1. Patients Served = Number of dispenses today
        dispenses = PharmacyDispense.objects.filter(
            visit__clinic_id=clinic_id,
            dispensed_at__date=date_obj
        )
        patients_served = dispenses.count()
        
        # 2. Sales / Revenue (From Invoices)
        # Assuming VisitInvoice reflects pharmacy + others, we filter by ChargeType if possible
        # Or just sum up invoices marked PAID today?
        # For specificity, let's use VisitCharge where type='MEDICINE'
        from django.db.models import Sum
        from .models import VisitCharge
        
        revenue = VisitCharge.objects.filter(
            visit_invoice__visit__clinic_id=clinic_id,
            visit_invoice__status='PAID',
            visit_invoice__updated_at__date=date_obj, # Paid Date
            charge_type='MEDICINE'
        ).aggregate(Sum('amount'))['amount__sum'] or 0.00
        
        # 3. Prescriptions Filled
        # Same as patients served if 1 dispense per visit? 
        # Let's count FormSubmissions that are fully dispensed
        
        return {
            "patients_served": patients_served,
            "prescriptions_filled": patients_served,
            "medicines_dispensed": 0, # Need granular item tracking for this
            "revenue": float(revenue)
        }

    @staticmethod
    def get_dashboard_metrics(clinic_id, date_param=None, service_id=None):
        """
        Returns real-time analytics for the clinic dashboard.
        Aggregates all departments or specific service.
        """
        from django.utils import timezone
        import datetime
        from django.db.models import Sum
        from .models import VisitCharge
        
        target_date = timezone.now().date()
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError: pass

        yesterday_date = target_date - datetime.timedelta(days=1)

        # SERVICE SPECIFIC ANYLTICS
        if service_id:
            # 1. Bookings (Total Visits)
            bookings_today = Visit.objects.filter(clinic_id=clinic_id, service_id=service_id, created_at__date=target_date).count()
            bookings_yesterday = Visit.objects.filter(clinic_id=clinic_id, service_id=service_id, created_at__date=yesterday_date).count()
            
            # 2. Revenue (From Invoices linked to Visits of this service)
            # This assumes VisitInvoice is created for the visit
            revenue_today = VisitCharge.objects.filter(
                visit_invoice__visit__clinic_id=clinic_id,
                visit_invoice__visit__service_id=service_id,
                visit_invoice__status='PAID',
                visit_invoice__updated_at__date=target_date
            ).aggregate(Sum('amount'))['amount__sum'] or 0.00
            
            revenue_yesterday = VisitCharge.objects.filter(
                visit_invoice__visit__clinic_id=clinic_id,
                visit_invoice__visit__service_id=service_id,
                visit_invoice__status='PAID',
                visit_invoice__updated_at__date=yesterday_date
            ).aggregate(Sum('amount'))['amount__sum'] or 0.00

            # 3. Profile Views (Mock for now, or track in AuditLog)
            profile_views = 0 
            
            # 4. Avg Rating (Mock for now)
            avg_rating = 4.8

            return {
                "bookings": {"value": bookings_today, "change": ClinicAnalyticsService._get_trend(bookings_today, bookings_yesterday)},
                "revenue": {"value": float(revenue_today), "change": ClinicAnalyticsService._get_trend(float(revenue_today), float(revenue_yesterday))},
                "profile_views": {"value": profile_views, "change": 0},
                "avg_rating": {"value": avg_rating, "change": 0},
                # Recent Activity Link
                "recent_activity": [
                    # Fetch last 3 visits
                    {
                        "title": f"New Booking: {v.pet.name}", 
                        "subtitle": v.created_at.strftime("%H:%M"), 
                        "icon": "tabler-calendar-plus"
                    }
                    for v in Visit.objects.filter(clinic_id=clinic_id, service_id=service_id).order_by('-created_at')[:3]
                ]
            }

        # CLINIC WIDE ANALYTICS
        reception = ClinicAnalyticsService.get_reception_metrics(clinic_id, target_date)
        vitals = ClinicAnalyticsService.get_vitals_metrics(clinic_id, target_date)
        doctor = ClinicAnalyticsService.get_doctor_metrics(clinic_id, target_date)
        lab = ClinicAnalyticsService.get_lab_metrics(clinic_id, target_date)
        pharmacy = ClinicAnalyticsService.get_pharmacy_metrics(clinic_id, target_date)
        
        # Executive Summary (Trends)
        
        # Function to get key metric for yesterday
        def get_yesterday_count(metric_type):
            if metric_type == 'visits':
                return Visit.objects.filter(clinic_id=clinic_id, created_at__date=yesterday_date).count()
            if metric_type == 'vitals':
                return Visit.objects.filter(clinic_id=clinic_id, vitals_completed_at__date=yesterday_date).count()
            if metric_type == 'doctor':
                return Visit.objects.filter(clinic_id=clinic_id, doctor_started_at__date=yesterday_date).count()
            if metric_type == 'lab':
                 return Visit.objects.filter(clinic_id=clinic_id, lab_completed_at__date=yesterday_date).count()
            if metric_type == 'pharmacy':
                 return PharmacyDispense.objects.filter(visit__clinic_id=clinic_id, dispensed_at__date=yesterday_date).count()
            return 0
            
        executive = {
            "total_visits": {
                "today": reception['today_visits'],
                "yesterday": get_yesterday_count('visits'),
                "trend": ClinicAnalyticsService._get_trend(reception['today_visits'], get_yesterday_count('visits'))
            },
            "vitals_done": {
                "today": vitals['vitals_completed'],
                "yesterday": get_yesterday_count('vitals'),
                "trend": ClinicAnalyticsService._get_trend(vitals['vitals_completed'], get_yesterday_count('vitals'))
            },
            "doctor_consultations": {
                "today": doctor['patients_seen'],
                "yesterday": get_yesterday_count('doctor'),
                "trend": ClinicAnalyticsService._get_trend(doctor['patients_seen'], get_yesterday_count('doctor'))
            },
            "lab_tests": {
                "today": lab['reports_completed'],
                "yesterday": get_yesterday_count('lab'),
                "trend": ClinicAnalyticsService._get_trend(lab['reports_completed'], get_yesterday_count('lab'))
            },
            "pharmacy_sales": { # Using count of dispenses for now as proxy for volume
                "today": pharmacy['patients_served'],
                "yesterday": get_yesterday_count('pharmacy'),
                "trend": ClinicAnalyticsService._get_trend(pharmacy['patients_served'], get_yesterday_count('pharmacy'))
            }
        }

        return {
            "date": str(target_date),
            "executive": executive,
            "reception": reception,
            "vitals": vitals,
            "doctor": doctor,
            "lab": lab,
            "pharmacy": pharmacy
        }

    @staticmethod
    def get_live_summary(clinic_id, user_id=None, date_param=None):
        """
        Returns PREMIUM real-time operational summary.
        dfate_param: YYYY-MM-DD (Defaults to Today)
        """
        from django.utils import timezone
        import datetime
        from django.db.models import Count, Case, When, Value, IntegerField
        from django.db.models.functions import TruncDate
        from .models import Visit, Pet, FormSubmission, VeterinaryAuditLog
        
        target_date = timezone.now().date()
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError: pass

        yesterday = target_date - datetime.timedelta(days=1)
        
        # --- 1. CURRENT STATS (Labelled 'today' for frontend compat) ---
        visits_today = Visit.objects.filter(clinic_id=clinic_id, created_at__date=target_date)
        
        # Avg Wait (Check-in to Doctor Start)
        started_visits = visits_today.filter(doctor_started_at__isnull=False, checked_in_at__isnull=False)
        avg_wait = 0
        if started_visits.exists():
            total_wait = sum((v.doctor_started_at - v.checked_in_at).total_seconds() for v in started_visits)
            avg_wait = int((total_wait / started_visits.count()) / 60)

        # --- 2. YESTERDAY STATS ---
        visits_yesterday = Visit.objects.filter(clinic_id=clinic_id, created_at__date=yesterday)
        started_yesterday = visits_yesterday.filter(doctor_started_at__isnull=False, checked_in_at__isnull=False)
        avg_wait_yest = 0
        if started_yesterday.exists():
            total_wait_y = sum((v.doctor_started_at - v.checked_in_at).total_seconds() for v in started_yesterday)
            avg_wait_yest = int((total_wait_y / started_yesterday.count()) / 60)

        data_yesterday = {
             "visits": visits_yesterday.count(),
             "avg_wait_time": avg_wait_yest,
             "completed": visits_yesterday.filter(status__in=['TREATMENT_COMPLETED', 'CLOSED']).count()
        }

        # --- 3. LIVE QUEUE (Active) ---
        queue_qs = visits_today.exclude(status__in=['TREATMENT_COMPLETED', 'CLOSED']).annotate(
            sort_priority=Case(
                When(status='CHECKED_IN', then=Value(1)),
                When(status='VITALS_RECORDED', then=Value(2)),
                When(status='DOCTOR_ASSIGNED', then=Value(3)),
                default=Value(10),
                output_field=IntegerField(),
            )
        ).order_by('sort_priority', 'created_at')[:15] # Top 15
        
        queue_data = []
        for v in queue_qs:
            handled_by = "Pending"
            if v.status == 'DOCTOR_ASSIGNED':
                handled_by = "Doctor"
            elif v.status == 'VITALS_RECORDED':
                handled_by = "Nurse" 
            
            queue_data.append({
                "id": str(v.id),
                "pet_name": v.pet.name,
                "owner": v.pet.owner.name if v.pet.owner else "Guest",
                "status": v.status,
                "time": v.updated_at.strftime("%H:%M"),
                "handled_by": handled_by
            })

        # --- 4. MY WORK (Staff Productivity) ---
        my_work = {"registered": 0, "vitals": 0, "consulted": 0, "completed": 0}
        if user_id:
            try:
                from django.db.models import Q
                
                my_work["registered"] = VeterinaryAuditLog.objects.filter(
                    visit__clinic_id=clinic_id,
                    performed_by=user_id,
                    action_type='VISIT_CREATED',
                    created_at__date=target_date
                ).count() or Pet.objects.filter(
                    owner__clinic_id=clinic_id, 
                    created_by=user_id, 
                    created_at__date=target_date
                ).count()
                
                my_work["vitals"] = VeterinaryAuditLog.objects.filter(
                    visit__clinic_id=clinic_id,
                    performed_by=user_id,
                    action_type='VITALS_ENTERED',
                    created_at__date=target_date
                ).count() or FormSubmission.objects.filter(
                    visit__clinic_id=clinic_id, 
                    submitted_by=user_id, 
                    form_definition__code='VITALS', 
                    created_at__date=target_date
                ).count()
                
                my_work["consulted"] = VeterinaryAuditLog.objects.filter(
                    visit__clinic_id=clinic_id,
                    performed_by=user_id,
                    action_type__in=['PRESCRIPTION_CREATED', 'LAB_ORDERED'],
                    created_at__date=target_date
                ).count() or FormSubmission.objects.filter(
                    visit__clinic_id=clinic_id, 
                    submitted_by=user_id, 
                    form_definition__code__in=['PRESCRIPTION', 'LAB_ORDER'], 
                    created_at__date=target_date
                ).count()
                
                my_work["completed"] = VeterinaryAuditLog.objects.filter(
                    visit__clinic_id=clinic_id,
                    performed_by=user_id,
                    action_type='STATUS_CHANGE',
                    created_at__date=target_date
                ).filter(
                    Q(metadata__new_status='TREATMENT_COMPLETED') | 
                    Q(metadata__new_status='CLOSED') |
                    Q(metadata__new_status='MEDICINES_DISPENSED')
                ).count()
            except Exception as e:
                pass

        # --- Granular Breakdown ---
        # 1. Waiting (Checked In, Not yet Vitals or Doctor)
        waiting = visits_today.filter(status__in=['CHECKED_IN'])
        
        # 2. Vitals (In Queue or Being Recorded)
        # Note: VITALS_RECORDED means they represent ready for Doctor, but we can group them here or in Doctor Queue.
        # Let's say: 
        # Waiting = CHECKED_IN
        # Vitals = In Vitals Queue? (Actually CHECKED_IN is the Vitals Queue). 
        # Let's align with the Queues:
        # Waiting Room = CREATED
        # Vitals Queue = CHECKED_IN
        # Doctor Queue = VITALS_RECORDED + DOCTOR_ASSIGNED + LAB_COMPLETED
        # Labs Queue = LAB_REQUESTED
        # Pharmacy Queue = PRESCRIPTION_FINALIZED
        
        # Revised: 
        # Waiting (Reception) = CREATED
        waiting_count = visits_today.filter(status='CREATED').count()
        # Vitals Pending = CHECKED_IN
        vitals_count = visits_today.filter(status='CHECKED_IN').count()
        # Doctor Pending = VITALS_RECORDED + DOCTOR_ASSIGNED
        doctor_count = visits_today.filter(status__in=['VITALS_RECORDED', 'DOCTOR_ASSIGNED']).count()
        # Labs Pending = LAB_REQUESTED
        labs_count = visits_today.filter(status='LAB_REQUESTED').count()
        # Pharmacy Pending = PRESCRIPTION_FINALIZED + LAB_COMPLETED (if no meds yet) or MEDICINES_DISPENSED?
        # Typically Pharmacy bucket shows those needing Dispense.
        pharmacy_count = visits_today.filter(status__in=['PRESCRIPTION_FINALIZED', 'LAB_COMPLETED']).count()

        completed_count = visits_today.filter(status__in=['TREATMENT_COMPLETED', 'CLOSED']).count()

        # Reminders for Today (Simple count)
        from .models import MedicationReminder
        reminders_count = MedicationReminder.objects.filter(visit__clinic_id=clinic_id, next_reminder_at__date=target_date).count()
        
        # Next Consultations (Scheduled for today, Status=CREATED) - Same as Waiting basically, but maybe distinguish?
        # For dashboard, "Waiting" usually means physically there. "Scheduled" means expecting.
        # Let's assume CREATED includes both.

        data_today = {
            "visits": visits_today.count(),
            "avg_wait_time": avg_wait,
            # Granular
            "waiting": waiting_count, # CREATED
            "vitals": vitals_count,   # CHECKED_IN
            "doctor": doctor_count,   # VITALS_RECORDED, DOCTOR_ASSIGNED
            "labs": labs_count,       # LAB_REQUESTED
            "pharmacy": pharmacy_count, # PRESCRIPTION_FINALIZED
            "completed": completed_count,
            "reminders": reminders_count
        }

        # --- 5. DETAILS (Popups) ---
        def serialize_visit_simple(qs):
             return [{
                "id": str(v.id),
                "pet_name": v.pet.name,
                "owner": v.pet.owner.name if v.pet.owner else "Guest",
                "status": v.status,
                "time": v.checked_in_at.strftime("%H:%M") if v.checked_in_at else v.created_at.strftime("%H:%M")
            } for v in qs]

        details = {
            "visits": serialize_visit_simple(visits_today.order_by('-created_at')),
            "waiting": serialize_visit_simple(visits_today.filter(status='CREATED').order_by('created_at')),
            "vitals": serialize_visit_simple(visits_today.filter(status='CHECKED_IN').order_by('created_at')),
            "doctor": serialize_visit_simple(visits_today.filter(status__in=['VITALS_RECORDED', 'DOCTOR_ASSIGNED']).order_by('created_at')),
            "labs": serialize_visit_simple(visits_today.filter(status='LAB_REQUESTED').order_by('created_at')),
            "pharmacy": serialize_visit_simple(visits_today.filter(status__in=['PRESCRIPTION_FINALIZED', 'LAB_COMPLETED']).order_by('created_at')),
            "completed": serialize_visit_simple(visits_today.filter(status__in=['TREATMENT_COMPLETED', 'CLOSED']).order_by('-updated_at'))
        }

        # --- 6. TREND (Last 7 Days) ---
        seven_days_ago = target_date - datetime.timedelta(days=7)
        trend_qs = Visit.objects.filter(
            clinic_id=clinic_id, 
            created_at__date__gte=seven_days_ago
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            visits=Count('id')
        ).order_by('date')
        
        trend_data = [{"date": str(getItem['date']), "visits": getItem['visits']} for getItem in trend_qs]

        return {
            "today": data_today,
            "yesterday": data_yesterday,
            "queue": queue_data,
            "my_work": my_work,
            "trend": trend_data,
            "details": details,
            "debug": {
                "user_id": user_id,
                "target_date": str(target_date),
                "clinic_id": clinic_id
            }
        }

class RolePermissionService:
    ROLE_PERMISSIONS = {
        'Receptionist': ['VETERINARY_CORE', 'VETERINARY_VISITS', 'VETERINARY_SCHEDULE', 'VETERINARY_ADMIN_SETTINGS', 'VETERINARY_VACCINES'],
        'Doctor': ['VETERINARY_CORE', 'VETERINARY_DOCTOR', 'VETERINARY_PRESCRIPTIONS'],
        'Nurse': ['VETERINARY_CORE', 'VETERINARY_VISITS', 'VETERINARY_VITALS', 'VETERINARY_VACCINES', 'VETERINARY_LABS'],
        'Lab Technician': ['VETERINARY_CORE', 'VETERINARY_LABS'],
        'Pharmacist': ['VETERINARY_CORE', 'VETERINARY_PHARMACY', 'VETERINARY_MEDICINE_REMINDERS', 'VETERINARY_PRESCRIPTIONS'],
        'Admin': ['VETERINARY_CORE', 'VETERINARY_ADMIN', 'VETERINARY_ADMIN_SETTINGS', 'VETERINARY_VISITS', 'VETERINARY_VITALS', 'VETERINARY_PRESCRIPTIONS', 'VETERINARY_LABS', 'VETERINARY_VACCINES', 'VETERINARY_MEDICINE_REMINDERS', 'VETERINARY_PHARMACY', 'VETERINARY_DOCTOR', 'VETERINARY_SCHEDULE', 'VETERINARY_ONLINE_CONSULT'],
        'Vitals Staff': ['VETERINARY_CORE', 'VETERINARY_VITALS']
    }

    @staticmethod
    def get_permissions_for_role(role_name, organization_id=None):
        """
        Dynamically resolve permissions for a role.
        Priority: 
        1. Live call to Service Provider Service (for Custom Roles)
        2. Hardcoded defaults (for System Roles)
        """
        if not role_name:
            return ['VETERINARY_CORE']

        # 1. Dynamic Resolution (Internal API Call)
        if organization_id:
            try:
                # Clean role name for URL (no spaces etc)
                import urllib.parse
                safe_role = urllib.parse.quote(role_name)
                url = f"http://127.0.0.1:8002/api/provider/roles/resolve/?org_id={organization_id}&role_name={safe_role}"
                
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        caps = data.get('capabilities')
                        if caps:
                            print(f"✅ Resolved role '{role_name}' dynamically from Provider Service.")
                            return caps
            except Exception as e:
                # Silent fail, fallback to hardcoded
                print(f"⚠️ Failed to resolve role '{role_name}' dynamically: {e}")

        # 2. Hardcoded Fallback
        for key, perms in RolePermissionService.ROLE_PERMISSIONS.items():
            if key.lower() == role_name.lower():
                return perms
        
        return ['VETERINARY_CORE'] # Absolute fallback
