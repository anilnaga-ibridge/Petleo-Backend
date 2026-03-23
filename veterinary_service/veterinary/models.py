
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# ========================
# STATIC CORE MODELS
# ========================

class Clinic(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    organization_id = models.CharField(
        max_length=255, 
        db_column='provider_id', 
        db_index=True,
        help_text="ID from Auth Service (Organization Owner ID)"
    )
    is_primary = models.BooleanField(default=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    subscription_plan = models.CharField(max_length=100, default='BASIC', help_text="Current plan (BASIC, PRO, ENTERPRISE)")
    capabilities = models.JSONField(default=dict, blank=True, help_text="Synced from Provider Service")
    
    def __str__(self):
        return self.name

class VeterinaryStaff(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user_id = models.CharField(max_length=255, unique=True, help_text="ID from Auth Service")
    full_name = models.CharField(max_length=255, blank=True, null=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, related_name='staff', null=True, blank=True, help_text="DEPRECATED: Use StaffClinicAssignment for multi-clinic support")
    role = models.CharField(max_length=50, blank=True, null=True)
    permissions = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Staff {self.auth_user_id} ({self.role})"

class StaffClinicAssignment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(VeterinaryStaff, on_delete=models.CASCADE, related_name='clinic_assignments')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='staff_assignments')
    role = models.CharField(max_length=50, blank=True, null=True)
    permissions = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    is_online_available = models.BooleanField(default=False)
    
    # Pro Doctor Features (Synced from Service Provider)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    consultation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('staff', 'clinic')

    def __str__(self):
        return f"{self.staff.auth_user_id} @ {self.clinic.name}"

class PetOwner(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='owners')
    auth_user_id = models.CharField(max_length=255, help_text="ID from Auth Service", null=True, blank=True)
    name = models.CharField(max_length=255, default="Unknown")
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50)
    address = models.TextField(blank=True, null=True)
    created_by = models.CharField(max_length=255, null=True, blank=True, help_text="Auth User ID of staff who registered this owner")
    
    class Meta:
        unique_together = ('clinic', 'phone')

    def __str__(self):
        return f"Owner {self.phone}"

class Pet(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(PetOwner, on_delete=models.CASCADE, related_name='pets')
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    external_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True,
        help_text="ID from customer_service for cross-service lookup"
    )
    name = models.CharField(max_length=255, default="Unknown Pet")
    species = models.CharField(max_length=100, blank=True, null=True)
    breed = models.CharField(max_length=100, blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True, help_text="Male, Female, etc.")
    dob = models.DateField(blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    weight = models.FloatField(blank=True, null=True, help_text="Weight in kg")
    notes = models.TextField(blank=True, null=True)
    tag = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.TextField(blank=True, null=True, help_text="Base64 encoded image or URL")
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=255, null=True, blank=True, help_text="Auth User ID of staff who registered this pet")
    
    def __str__(self):
        return f"{self.name} ({self.species})"

class Visit(TimeStampedModel):
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('CHECKED_IN', 'Checked In'),
        ('VITALS_RECORDED', 'Vitals Recorded'),
        ('DOCTOR_ASSIGNED', 'Doctor Assigned'),
        ('LAB_REQUESTED', 'Lab Requested'),
        ('LAB_COMPLETED', 'Lab Completed'),
        ('PRESCRIPTION_FINALIZED', 'Prescription Finalized'),
        ('MEDICINES_DISPENSED', 'Medicines Dispensed'),
        ('TREATMENT_COMPLETED', 'Treatment Completed'),
        ('CLOSED', 'Closed'),
    ]

    VISIT_TYPE_CHOICES = [
        ('OFFLINE', 'Offline'),
        ('ONLINE', 'Online'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='visits')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='visits')
    appointment = models.OneToOneField(
        'MedicalAppointment', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='visit'
    )
    service_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID of the service (Grooming, Veterinary, etc.)")
    status = models.CharField(max_length=30, choices=[
        ('CREATED', 'Created'),
        ('CHECKED_IN', 'Checked In'),
        ('VITALS_RECORDED', 'Vitals Recorded'),
        ('CONSULTATION_IN_PROGRESS', 'Consultation In Progress'),
        ('COMPLETED', 'Completed'),
        ('CLOSED', 'Closed'),
        # Legacy/Detailed statuses (keeping for transition safety)
        ('DOCTOR_ASSIGNED', 'Doctor Assigned'),
        ('LAB_REQUESTED', 'Lab Requested'),
        ('LAB_COMPLETED', 'Lab Completed'),
        ('PRESCRIPTION_FINALIZED', 'Prescription Finalized'),
    ], default='CREATED')
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='OFFLINE')
    reason = models.TextField(blank=True, null=True, help_text="Reason for the visit / Chief Complaint")
    consultation_notes = models.TextField(blank=True, null=True, help_text="SOAP notes / Clinical findings")
    
    # [NEW] Triage Fields
    PRIORITY_CHOICES = [
        ('P1', 'Critical (P1)'),
        ('P2', 'Urgent (P2)'),
        ('P3', 'Routine (P3)'),
    ]
    priority = models.CharField(max_length=5, choices=PRIORITY_CHOICES, default='P3')
    triage_notes = models.TextField(blank=True, null=True)
    
    # Audit & Assignment
    assigned_doctor_auth_id = models.CharField(max_length=255, null=True, blank=True, help_text="Auth ID of the assigned doctor")
    queue_entered_at = models.DateTimeField(auto_now_add=True, null=True)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # SLA / Timeline Fields
    checked_in_at = models.DateTimeField(null=True, blank=True)
    vitals_started_at = models.DateTimeField(null=True, blank=True) # Added per spec
    vitals_completed_at = models.DateTimeField(null=True, blank=True)
    doctor_started_at = models.DateTimeField(null=True, blank=True)
    lab_ordered_at = models.DateTimeField(null=True, blank=True)
    lab_completed_at = models.DateTimeField(null=True, blank=True)
    prescription_finalized_at = models.DateTimeField(null=True, blank=True)
    pharmacy_completed_at = models.DateTimeField(null=True, blank=True) # Added per spec (alias for medicines_dispensed)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True, help_text="Auth User ID of staff who created this visit")
    
    def __str__(self):
        return f"Visit {self.id} ({self.status})"


class MedicalAppointment(TimeStampedModel):
    """
    Schedule-based appointments for Veterinary/Doctor consultations.
    Differs from generic bookings by requiring a specific Pet and Doctor role.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
        ('NO_SHOW', 'No Show'),
        ('COMPLETED', 'Completed'),
    ]

    CREATOR_CHOICES = [
        ('ONLINE', 'Online'),
        ('RECEPTIONIST', 'Receptionist'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(
        'StaffClinicAssignment', 
        on_delete=models.PROTECT, 
        related_name='medical_appointments',
        help_text="The specific doctor assigned to this appointment"
    )
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='appointments')
    service_id = models.CharField(max_length=255, null=True, blank=True, help_text="Reference to ProviderTemplateFacility in service_provider service")
    
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    created_by = models.CharField(max_length=20, choices=CREATOR_CHOICES, default='ONLINE')
    notes = models.TextField(blank=True, null=True)

    # Online booking linkage fields
    online_booking_id = models.UUIDField(
        null=True, blank=True,
        help_text="Links back to Booking.id in customer_service when created from online booking"
    )
    pet_owner_auth_id = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Auth user ID of the pet owner who made the online booking"
    )
    consultation_type = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Consultation type chosen by pet owner (e.g. General Checkup, Emergency)"
    )
    consultation_type_id = models.UUIDField(
        null=True, blank=True,
        help_text="Original ConsultationType UUID from service_provider_service"
    )
    consultation_mode = models.CharField(max_length=50, null=True, blank=True)
    meeting_room = models.CharField(max_length=255, null=True, blank=True)
    meeting_link = models.URLField(max_length=500, null=True, blank=True, help_text="Full URL for the video meeting room")
    consultation_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Fee for this consultation (snapshotted at time of appointment)"
    )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.meeting_room and self.consultation_mode == 'ONLINE':
            # Create a unique room ID based on the appointment ID or a random slug
            import uuid
            self.meeting_room = f"meet-{str(uuid.uuid4())[:8]}"
        
        super().save(*args, **kwargs)

        # Send notification for NEW online appointments
        if is_new and self.consultation_mode == 'ONLINE' and self.pet and self.pet.owner:
            try:
                # 1. Create a Visit record so it shows in Pet Owner's Care History
                from veterinary.models import Visit
                if not hasattr(self, 'visit'):
                    Visit.objects.create(
                        clinic=self.clinic,
                        pet=self.pet,
                        appointment=self,
                        status='CREATED',
                        visit_type='ONLINE'
                    )

                # 2. Trigger notification
                from notifications.service import NotificationService
                NotificationService.handle_event('ONLINE_CONSULTATION_CREATED', {
                    'owner_id': self.pet.owner.id,
                    'pet_name': self.pet.name,
                    'meeting_room': self.meeting_room,
                    'appointment_id': str(self.id)
                })
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to process online consult post-save: {e}")

    class Meta:
        ordering = ['appointment_date', 'start_time']
        verbose_name = "Medical Appointment"
        verbose_name_plural = "Medical Appointments"
        indexes = [
            models.Index(fields=['clinic', 'appointment_date', 'status']),
            models.Index(fields=['doctor', 'appointment_date', 'status']),
        ]

    def __str__(self):
        return f"Appt {self.appointment_date} with {self.doctor} for {self.pet.name}"

# ========================
# DYNAMIC FIELD ENGINE
# ========================

class DynamicFieldDefinition(TimeStampedModel):
    ENTITY_TYPES = [
        ('CLINIC', 'Clinic'),
        ('OWNER', 'Pet Owner'),
        ('PET', 'Pet'),
        ('VISIT', 'Visit'),
        ('VITALS', 'Vitals'),
        ('DIAGNOSIS', 'Diagnosis'),
        ('LAB', 'Lab Test'),
        ('PRESCRIPTION', 'Prescription'),
        ('VACCINE', 'Vaccine'),
    ]
    
    FIELD_TYPES = [
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('TEXTAREA', 'Textarea'),
        ('DATE', 'Date'),
        ('BOOLEAN', 'Boolean'),
        ('DROPDOWN', 'Dropdown'),
        ('MULTISELECT', 'Multi-Select'),
        ('FILE', 'File'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='field_definitions')
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES)
    key = models.CharField(max_length=50, help_text="Machine key, e.g., 'temperature_c'")
    label = models.CharField(max_length=100, help_text="UI Label")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True, help_text="Options for DROPDOWN/MULTISELECT")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('clinic', 'entity_type', 'key')
        ordering = ['order']

    def __str__(self):
        return f"{self.label} ({self.entity_type})"

class DynamicFieldValue(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(DynamicFieldDefinition, on_delete=models.PROTECT)
    entity_id = models.UUIDField(help_text="ID of the related entity (Visit, Pet, or Virtual UUID)")
    value = models.JSONField(help_text="Stores the actual value")
    
    class Meta:
        indexes = [
            models.Index(fields=['entity_id']),
            models.Index(fields=['definition']),
        ]

# ========================
# PHASE 2: METADATA ENGINE
# ========================

class FormDefinition(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text="Unique code e.g. VITALS_FORM")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='forms', null=True, blank=True, help_text="Null for global forms")

    def __str__(self):
        return f"{self.name} ({self.code})"

class FormField(TimeStampedModel):
    FIELD_TYPES = [
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('SELECT', 'Select'),
        ('BOOLEAN', 'Boolean'),
        ('DATE', 'Date'),
        ('TEXTAREA', 'Textarea'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_definition = models.ForeignKey(FormDefinition, on_delete=models.CASCADE, related_name='fields')
    field_key = models.CharField(max_length=50, help_text="Key for JSON storage e.g. temperature")
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    unit = models.CharField(max_length=20, blank=True, null=True, help_text="e.g. kg, bpm")
    is_required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True, help_text="Extra config like select options")

    class Meta:
        ordering = ['order']
        unique_together = ('form_definition', 'field_key')

    def __str__(self):
        return f"{self.label} ({self.field_key})"

class FieldValidation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name='validations')
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    regex = models.CharField(max_length=255, null=True, blank=True)
    error_message = models.CharField(max_length=255, null=True, blank=True)

class FormSubmission(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_definition = models.ForeignKey(FormDefinition, on_delete=models.PROTECT, related_name='submissions')
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='form_submissions')
    submitted_by = models.CharField(max_length=255, help_text="Auth User ID")
    data = models.JSONField(default=dict)

    def __str__(self):
        return f"Submission for {self.form_definition.code} in Visit {self.visit.id}"

# ========================
# PHASE 3: EXECUTION LAYER
# ========================

class PharmacyDispense(TimeStampedModel):
    DISPENSE_STATUS = [
        ('DISPENSED', 'Dispensed'),
        ('PARTIAL', 'Partial'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='dispenses')
    prescription_submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='dispenses')
    dispensed_by = models.CharField(max_length=255, help_text="Auth User ID")
    dispensed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=DISPENSE_STATUS, default='DISPENSED')

    def __str__(self):
        return f"Dispense for Visit {self.visit.id}"

class MedicationReminder(TimeStampedModel):
    REMINDER_STATUS = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('MISSED', 'Missed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='reminders')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='reminders')
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100, help_text="e.g. '1-0-1' or 'Once a day'")
    start_date = models.DateField()
    end_date = models.DateField()
    next_reminder_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=REMINDER_STATUS, default='ACTIVE')

    def __str__(self):
        return f"Reminder for {self.medicine_name} ({self.pet.id})"

# ========================
# LAB & PHARMACY MASTER MODELS
# ========================

class LabTest(TimeStampedModel):
    """
    Master list of available Lab Tests (created by Super Admin or Clinic Admin).
    """
    CATEGORY_CHOICES = [
        ('BLOOD', 'Blood Test'),
        ('XRAY', 'X-Ray'),
        ('SCAN', 'Imaging/Scan'),
        ('URINE', 'Urine Analysis'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='lab_tests', null=True, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='BLOOD')
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    duration_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category})"

class Medicine(TimeStampedModel):
    """
    Pharmacy Inventory Master.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    stock_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    expiry_date = models.DateField(null=True, blank=True)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=10.00)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (Stock: {self.stock_quantity})"

class MedicineBatch(TimeStampedModel):
    """
    Individual lots/shipments of a medicine.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    initial_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    expiry_date = models.DateField()
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.medicine.name} - Batch {self.batch_number} (Exp: {self.expiry_date})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Sync master medicine total stock
        from django.db.models import Sum
        total = MedicineBatch.objects.filter(
            medicine=self.medicine, 
            is_active=True,
            expiry_date__gte=self.expiry_date # Only count non-expired in master total? 
            # Actually, standard practice is to count all active current_quantity, but let's be strict
        ).aggregate(Sum('current_quantity'))['current_quantity__sum'] or 0
        
        self.medicine.stock_quantity = total
        self.medicine.save()

    class Meta:
        ordering = ['expiry_date'] # FIFO base

class Prescription(TimeStampedModel):
    """
    Formal Prescription Record created during consultation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='prescriptions')
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    doctor_auth_id = models.CharField(max_length=255)
    medicine_name = models.CharField(max_length=200, null=True, blank=True)
    dosage = models.CharField(max_length=200, null=True, blank=True)
    duration_days = models.IntegerField(default=1)
    notes = models.TextField(blank=True, null=True)
    prescription_file = models.FileField(upload_to='prescriptions/', null=True, blank=True)

    def __str__(self):
        return f"Prescription for Visit {self.visit.id}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    dosage = models.CharField(max_length=255, help_text="e.g. 1-0-1")
    duration_days = models.PositiveIntegerField(default=5)
    instructions = models.TextField(blank=True, null=True)

class PharmacyTransaction(TimeStampedModel):
    """
    Record of medicines dispensed, with price snapshot.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='pharmacy_transactions')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    dispensed_by = models.CharField(max_length=255)

    def __str__(self):
        return f"Dispensed {self.quantity} x {self.medicine.name}"

class VeterinaryAuditLog(TimeStampedModel):
    # (Rest of the file follows)
    ACTION_TYPES = [
        ('VISIT_CREATED', 'Visit Created'),
        ('STATUS_CHANGE', 'Status Change'),
        ('VITALS_ENTERED', 'Vitals Entered'),
        ('LAB_ORDERED', 'Lab Ordered'),
        ('LAB_RESULT_ADDED', 'Lab Result Added'),
        ('PRESCRIPTION_CREATED', 'Prescription Created'),
        ('MEDICINE_DISPENSED', 'Medicine Dispensed'),
        ('INVOICE_PAID', 'Invoice Paid'),
        ('MEDICAL_RECORD_VIEWED', 'Medical Record Viewed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='audit_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    performed_by = models.CharField(max_length=255, help_text="Auth User ID")
    capability_used = models.CharField(max_length=100, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.action_type} on Visit {self.visit.id} by {self.performed_by}"


# ========================
# PHASE 4: BILLING LAYER
# ========================

class VisitInvoice(TimeStampedModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('FINALIZED', 'Finalized'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='invoice')
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    consultation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    lab_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    medicine_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    other_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('FINALIZED', 'Finalized'),
        ('PAYMENT_PENDING', 'Payment Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')

    def __str__(self):
        return f"Invoice {self.id} for Visit {self.visit.id}"

    def finalize(self):
        """Locks the invoice and prepares it for payment."""
        self.recalculate_totals()
        self.status = 'FINALIZED'
        self.save()

    def recalculate_totals(self):
        items = self.items.all()
        self.subtotal = sum(item.total_price for item in items)
        # Assuming 0% tax for now, or can be configured
        self.tax = 0 
        self.total = self.subtotal + self.tax
        self.save()


class InvoiceLineItem(TimeStampedModel):
    CHARGE_TYPE_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Lab Test'),
        ('MEDICINE', 'Medicine'),
        ('PROCEDURE', 'Procedure'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(VisitInvoice, on_delete=models.CASCADE, related_name='items')
    charge_type = models.CharField(max_length=30, choices=CHARGE_TYPE_CHOICES)
    reference_id = models.UUIDField(null=True, blank=True, help_text="ID of lab_order / pharmacy_txn / etc.")
    
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1.00)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.description} ({self.total_price})"

    def save(self, *args, **kwargs):
        if not self.total_price:
            from decimal import Decimal
            self.total_price = Decimal(str(self.unit_price)) * Decimal(str(self.quantity))
        super().save(*args, **kwargs)
        if self.invoice:
            self.invoice.recalculate_totals()

# ========================
# PHASE 3.5: PROFESSIONAL LAB SYSTEM
# ========================

class LabTestTemplate(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g. CBC, LFT")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class LabTestField(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(LabTestTemplate, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField(max_length=255, help_text="e.g. Hemoglobin")
    unit = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. g/dL")
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.field_name} ({self.template.name})"

class LabOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ('LAB_REQUESTED', 'Requested'),
        ('IN_PROGRESS', 'In Progress'),
        ('LAB_COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='lab_orders')
    template = models.ForeignKey(LabTestTemplate, on_delete=models.PROTECT, related_name='orders')
    price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='LAB_REQUESTED')
    requested_by = models.CharField(max_length=255, help_text="Doctor Auth ID", blank=True, null=True)
    performed_by = models.CharField(max_length=255, help_text="Lab Tech Auth ID", blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.template.name} for Visit {self.visit.id}"

class LabResult(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='results')
    test_field = models.ForeignKey(LabTestField, on_delete=models.PROTECT) # Link to specific definition
    value = models.CharField(max_length=255, help_text="Measured Value")
    flag = models.CharField(max_length=20, blank=True, null=True, help_text="LOW, HIGH, NORMAL (Calculated)")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('lab_order', 'test_field')

    def __str__(self):
        return f"{self.test_field.field_name}: {self.value}"

# ========================
# PHASE 5: VACCINATION TRACKING
# ========================

class VaccineMaster(TimeStampedModel):
    """
    Master list of vaccines managed per clinic.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='vaccines')
    vaccine_name = models.CharField(max_length=255)
    species = models.CharField(max_length=100, help_text="e.g. Dog, Cat, Bird")
    default_interval_days = models.PositiveIntegerField(help_text="Days until next dose")
    required_doses = models.PositiveIntegerField(default=1)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('clinic', 'vaccine_name', 'species')
        verbose_name = "Vaccine Master"
        verbose_name_plural = "Vaccine Masters"

    def __str__(self):
        return f"{self.vaccine_name} ({self.species})"


class PetVaccinationRecord(TimeStampedModel):
    """
    Individual pet vaccination log.
    """
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('MISSED', 'Missed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='vaccination_records')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccination_records')
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name='administered_vaccines')
    vaccine = models.ForeignKey(VaccineMaster, on_delete=models.PROTECT, related_name='records')
    dose_number = models.PositiveIntegerField()
    administered_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    doctor = models.CharField(max_length=255, blank=True, null=True, help_text="Auth ID of administering doctor")
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')

    class Meta:
        unique_together = ('pet', 'vaccine', 'dose_number')
        indexes = [
            models.Index(fields=['pet', 'vaccine']),
            models.Index(fields=['next_due_date', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Auto-calculate next due date if administered date is set
        if self.administered_date and not self.next_due_date:
            from datetime import timedelta
            self.next_due_date = self.administered_date + timedelta(days=self.vaccine.default_interval_days)
            
        # If no dates are provided at all (e.g. pure scheduling), fallback to today + interval
        elif not self.administered_date and not self.next_due_date:
            from datetime import date, timedelta
            self.next_due_date = date.today() + timedelta(days=self.vaccine.default_interval_days)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pet.name} - {self.vaccine.vaccine_name} Dose {self.dose_number}"


class VaccinationReminder(TimeStampedModel):
    """
    Notification trigger for due vaccinations.
    """
    REMINDER_TYPE_CHOICES = [
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('WHATSAPP', 'WhatsApp'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vaccination_record = models.ForeignKey(PetVaccinationRecord, on_delete=models.CASCADE, related_name='reminders')
    reminder_date = models.DateField()
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES, default='SMS')
    sent_status = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder for {self.vaccination_record} on {self.reminder_date}"

class PreVisitForm(models.Model):
    """
    Form filled by pet owners before the visit (History, symptoms, etc).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='pre_visit_form')
    
    # Secure token for public link access without authentication
    access_token = models.CharField(max_length=64, unique=True, default=uuid.uuid4().hex)
    
    # Form data (History, reason for visit, current symptoms, etc.)
    data = models.JSONField(default=dict)
    
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pre-Visit Form for {self.visit}"

# ==========================================
# PHASE 6: ESTIMATES MODULE
# ==========================================

class TreatmentEstimate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='estimates')
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent to Owner'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('INVOICED', 'Converted to Invoice'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.CharField(max_length=100, help_text="Doctor auth ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Estimate {self.id} for Visit {self.visit_id}"

    def recalculate_totals(self):
        total = self.items.aggregate(models.Sum('total_price'))['total_price__sum'] or 0.00
        self.total_amount = total
        self.save()

class EstimateLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estimate = models.ForeignKey(TreatmentEstimate, on_delete=models.CASCADE, related_name='items')
    
    CHARGE_TYPE_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Laboratory'),
        ('MEDICINE', 'Pharmacy/Medicine'),
        ('SURGERY', 'Surgery'),
        ('OTHER', 'Other'),
    ]
    charge_type = models.CharField(max_length=20, choices=CHARGE_TYPE_CHOICES, default='OTHER')
    
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        self.estimate.recalculate_totals()


# ==========================================
# PHASE 7: PREVENTIVE & REMINDERS (RESTORED)
# ==========================================

class MedicineReminder(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='medicine_reminders')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='reminders')
    pet_owner_auth_id = models.CharField(max_length=255, help_text="Auth User ID of the pet owner")
    doctor_auth_id = models.CharField(max_length=255, null=True, blank=True, help_text="Auth User ID of the doctor")
    created_by_auth_id = models.CharField(max_length=255, null=True, blank=True, help_text="Auth User ID of the creator")
    
    dosage = models.CharField(max_length=100)
    food_instruction = models.CharField(max_length=20, choices=[
        ('BEFORE_FOOD', 'Before Food'),
        ('AFTER_FOOD', 'After Food'),
        ('WITH_FOOD', 'With Food')
    ])
    reminder_times = models.JSONField(help_text="List of reminder times in HH:MM format")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Reminder for {self.pet.name} - {self.medicine.name}"

class MedicineReminderSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reminder = models.ForeignKey(MedicineReminder, on_delete=models.CASCADE, related_name='schedules')
    scheduled_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('TAKEN', 'Taken'),
        ('MISSED', 'Missed')
    ], default='PENDING')
    taken_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['scheduled_datetime']

class Vaccination(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='system_vaccinations')
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_vaccinations_given')
    vaccine_name = models.CharField(max_length=255)
    date_given = models.DateField()
    next_due_date = models.DateField()
    doctor_id = models.CharField(max_length=255, null=True, blank=True, help_text="Auth ID of administering doctor")
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'vaccinations'
        ordering = ['-date_given']

class Deworming(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='system_deworming_records')
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_deworming_given')
    medicine_name = models.CharField(max_length=255)
    date_given = models.DateField()
    next_due_date = models.DateField()
    doctor_id = models.CharField(max_length=255, null=True, blank=True, help_text="Auth ID of administering doctor")

    class Meta:
        db_table = 'deworming_records'
        ordering = ['-date_given']

class SystemVaccinationReminder(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='system_vaccination_reminders')
    pet_owner_id = models.CharField(max_length=255, help_text="Auth ID of pet owner")
    vaccine_name = models.CharField(max_length=255)
    next_due_date = models.DateField()
    reminder_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('SENT', 'Sent')], default='PENDING')

    class Meta:
        db_table = 'vaccination_reminders'
        ordering = ['reminder_date']

class SystemDewormingReminder(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partition_clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='system_deworming_reminders')
    pet_owner_id = models.CharField(max_length=255, help_text="Auth ID of pet owner")
    medicine_name = models.CharField(max_length=255)
    next_due_date = models.DateField()
    reminder_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('SENT', 'Sent')], default='PENDING')

    class Meta:
        db_table = 'deworming_reminders'
        ordering = ['reminder_date']

class VisitStatusHistory(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)
    changed_by_user_id = models.CharField(max_length=255, help_text="Auth User ID of who changed it")
    changed_by_role = models.CharField(max_length=50, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

class ClinicSettings(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE, related_name='settings')
    clinic_name = models.CharField(max_length=200)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    working_hours = models.JSONField(default=dict)

class ClinicSubscription(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE, related_name='subscription_record')
    plan_id = models.UUIDField(db_index=True)
    plan_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('EXPIRED', 'Expired'), ('TRIAL', 'Trial')], default='TRIAL')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

class Vitals(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='vitals_record')
    weight = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    pulse = models.IntegerField(null=True, blank=True)
    respiration = models.IntegerField(null=True, blank=True)
    symptoms = models.TextField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

# ========================
# SAAS PHARMACY FULFILLMENT
# ========================

class PharmacyOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('STOCK_CHECKED', 'Stock Checked'),
        ('PARTIAL_APPROVED', 'Partial Approved'),
        ('OTP_SENT', 'OTP Sent'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='pharmacy_orders')
    visit = models.OneToOneField(Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_order')
    pet_name = models.CharField(max_length=255, blank=True)
    owner_name = models.CharField(max_length=255, blank=True)
    owner_phone = models.CharField(max_length=50, blank=True)
    owner_email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    completed_at = models.DateTimeField(null=True, blank=True)
    pharmacist_auth_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} ({self.status})"

class PharmacyOrderItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(PharmacyOrder, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='order_items')
    quantity_prescribed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_dispensed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity_prescribed}"

class OtpVerification(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(PharmacyOrder, on_delete=models.CASCADE, related_name='otp_verification')
    otp_code = models.CharField(max_length=10)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for Order {self.order.id}"
