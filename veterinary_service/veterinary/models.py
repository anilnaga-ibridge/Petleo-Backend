
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
    capabilities = models.JSONField(default=dict, blank=True, help_text="Synced from Provider Service")
    
    def __str__(self):
        return self.name

class VeterinaryStaff(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user_id = models.CharField(max_length=255, unique=True, help_text="ID from Auth Service")
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
    
    class Meta:
        unique_together = ('clinic', 'phone')

    def __str__(self):
        return f"Owner {self.phone}"

class Pet(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(PetOwner, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=255, default="Unknown Pet")
    species = models.CharField(max_length=100, blank=True, null=True)
    breed = models.CharField(max_length=100, blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True, help_text="Male, Female, etc.")
    dob = models.DateField(blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    weight = models.FloatField(blank=True, null=True, help_text="Weight in kg")
    notes = models.TextField(blank=True, null=True)
    tag = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
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
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='CREATED')
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='OFFLINE')
    reason = models.TextField(blank=True, null=True, help_text="Reason for the visit / Chief Complaint")
    
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
    
    def __str__(self):
        return f"Visit {self.id} ({self.status})"

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

class VeterinaryAuditLog(TimeStampedModel):
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
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='invoice')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    def __str__(self):
        return f"Invoice {self.id} for Visit {self.visit.id}"

    def recalculate_totals(self):
        charges = self.charges.all()
        self.subtotal = sum(charge.amount for charge in charges)
        # Assuming 0% tax for now, or can be configured
        self.tax = 0 
        self.total = self.subtotal + self.tax
        self.save()


class VisitCharge(TimeStampedModel):
    CHARGE_TYPE_CHOICES = [
        ('CONSULTATION', 'Consultation'),
        ('LAB', 'Lab Test'),
        ('MEDICINE', 'Medicine'),
        ('VITALS', 'Vitals'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit_invoice = models.ForeignKey(VisitInvoice, on_delete=models.CASCADE, related_name='charges')
    charge_type = models.CharField(max_length=30, choices=CHARGE_TYPE_CHOICES)
    reference_id = models.UUIDField(null=True, blank=True, help_text="ID of lab_id / prescription_id / etc.")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.charge_type} Charge: {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.visit_invoice.recalculate_totals()

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
