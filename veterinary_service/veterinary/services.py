import uuid
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
    def get_dashboard_metrics(clinic_id, date_param=None):
        """
        Returns real-time analytics for the clinic dashboard.
        Aggregates all departments.
        """
        from django.utils import timezone
        import datetime
        
        target_date = timezone.now().date()
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError: pass

        reception = ClinicAnalyticsService.get_reception_metrics(clinic_id, target_date)
        vitals = ClinicAnalyticsService.get_vitals_metrics(clinic_id, target_date)
        doctor = ClinicAnalyticsService.get_doctor_metrics(clinic_id, target_date)
        lab = ClinicAnalyticsService.get_lab_metrics(clinic_id, target_date)
        pharmacy = ClinicAnalyticsService.get_pharmacy_metrics(clinic_id, target_date)
        
        # Executive Summary (Trends)
        yesterday_date = target_date - datetime.timedelta(days=1)
        
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
class RolePermissionService:
    ROLE_PERMISSIONS = {
        'Receptionist': ['VETERINARY_CORE', 'VETERINARY_VISITS', 'VETERINARY_SCHEDULE', 'VETERINARY_ADMIN_SETTINGS', 'VETERINARY_VACCINES'],
        'Doctor': ['VETERINARY_CORE', 'VETERINARY_DOCTOR', 'VETERINARY_PRESCRIPTIONS'],
        'Nurse': ['VETERINARY_CORE', 'VETERINARY_VISITS', 'VETERINARY_VITALS', 'VETERINARY_VACCINES', 'VETERINARY_LABS'],
        'Lab Technician': ['VETERINARY_CORE', 'VETERINARY_LABS'],
        'Pharmacist': ['VETERINARY_CORE', 'VETERINARY_PHARMACY', 'VETERINARY_MEDICINE_REMINDERS', 'VETERINARY_PRESCRIPTIONS'],
        'Admin': ['VETERINARY_CORE', 'VETERINARY_ADMIN', 'VETERINARY_ADMIN_SETTINGS', 'VETERINARY_VISITS', 'VETERINARY_VITALS', 'VETERINARY_PRESCRIPTIONS', 'VETERINARY_LABS', 'VETERINARY_VACCINES', 'VETERINARY_MEDICINE_REMINDERS', 'VETERINARY_PHARMACY', 'VETERINARY_DOCTOR']
    }

    @staticmethod
    def get_permissions_for_role(role_name):
        # Case insensitive lookup
        for key, perms in RolePermissionService.ROLE_PERMISSIONS.items():
            if key.lower() == role_name.lower():
                return perms
        return ['VETERINARY_CORE'] # Fallback default
