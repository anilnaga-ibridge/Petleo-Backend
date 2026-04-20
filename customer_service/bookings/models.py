import uuid
from django.db import models
from django.utils import timezone
from customers.models import PetOwnerProfile
from pets.models import Pet

from pets.models import Pet

class VisitGroup(models.Model):
    """
    Atomic unit for a multi-service cart. 
    Groups multiple BookingItems into a single conceptual visit.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(help_text="The clinic or provider where this visit takes place", db_index=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='visit_groups')
    owner = models.ForeignKey(PetOwnerProfile, on_delete=models.CASCADE, related_name='visit_groups')
    
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True, help_text="To prevent duplicate bookings on retries")
    
    status = models.CharField(max_length=20, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['idempotency_key']),
        ]

    def __str__(self):
        return f"Visit {self.id} - {self.status}"

class Booking(models.Model):
    """Parent model for a booking transaction (Header)"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SEARCHING_STAFF', 'Searching Staff'), # Tier 2 Initial State
        ('UNASSIGNED', 'Unassigned'),           # Tier 2 SLA Warning State
        ('PAID', 'Paid'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED_REQUEST', 'Expired Request'), # Rule 4
        ('RESCHEDULE_REQUIRED', 'Reschedule Required') # Rule 4
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(PetOwnerProfile, on_delete=models.CASCADE, related_name='bookings')
    
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='INR')
    
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Stripe Payment Tracking Fields
    payment_gateway = models.CharField(max_length=50, default='STRIPE')
    transaction_id = models.CharField(max_length=255, null=True, blank=True, help_text="Stripe checkout session ID or Payment Intent ID")
    checkout_session_url = models.URLField(max_length=1000, null=True, blank=True, help_text="Stripe hosted checkout URL")
    
    address_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of the address at time of booking")
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class BookingItem(models.Model):
    """Individual bookable items inside a Booking"""
    
    ITEM_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SEARCHING_STAFF', 'Searching Staff'),
        ('UNASSIGNED', 'Unassigned'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED_REQUEST', 'Expired Request'),
        ('RESCHEDULE_REQUIRED', 'Reschedule Required')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    visit_group = models.ForeignKey(VisitGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    # Target Info
    provider_id = models.UUIDField(help_text="UUID of the service provider")
    provider_auth_id = models.CharField(max_length=255, null=True, blank=True, help_text="Auth ID of the organization/clinic")
    assigned_employee_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID of the assigned employee")
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='booking_items')
    
    # Service Info
    service_id = models.CharField(max_length=255)
    facility_id = models.CharField(max_length=255)
    
    selected_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True, help_text="End time for range-based bookings (e.g. Boarding)")
    
    # Snapshots
    service_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of Service/Category/Facility names")
    price_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of pricing and billing units")
    addons_snapshot = models.JSONField(default=list, blank=True, help_text="List of selected add-ons")
    
    # Status & Management
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Completion OTP
    completion_otp = models.CharField(max_length=4, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['selected_time']
        indexes = [
            models.Index(fields=['provider_id', 'selected_time', 'end_time']),
            models.Index(fields=['assigned_employee_id', 'selected_time']),
            models.Index(fields=['pet', 'selected_time', 'end_time']),
            models.Index(fields=['visit_group']),
        ]

    def __str__(self):
        return f"Item {self.id} for Order {self.booking.id}"


class BookingStatusHistory(models.Model):
    """Audit trail for booking status changes (can track Header or Item)"""
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history', null=True, blank=True)
    booking_item = models.ForeignKey(BookingItem, on_delete=models.CASCADE, related_name='status_history', null=True, blank=True)
    
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.UUIDField(help_text="UUID of the user who performed the action")
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = "Booking Status Histories"

    def __str__(self):
        target = self.booking_item.id if self.booking_item else self.booking.id
        return f"{target}: {self.previous_status} -> {self.new_status}"


class InvoiceSequence(models.Model):
    """
    Tracks sequential invoice numbers per calendar year.
    Used for PO-YYYY-NNNNNN format.
    """
    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Invoice Sequence"
        verbose_name_plural = "Invoice Sequences"

    def __str__(self):
        return f"{self.year}: {self.last_number}"


class TaxConfiguration(models.Model):
    """
    Dynamic tax rates for different jurisdictions or services.
    """
    key = models.CharField(max_length=50, unique=True, help_text="e.g. GST_STANDARD, VAT_EUROPE")
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage rate (e.g. 18.00)")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.rate}%"


class Invoice(models.Model):
    """
    Production-grade invoice model with immutable snapshots of provider,
    customer, and service details at the moment of issuance.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
        ('CANCELLED', 'Cancelled'),
        ('VOID', 'Void'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, related_name='invoices')
    
    issued_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED')
    
    # Immutable Snapshots (Critical for production records)
    provider_snapshot = models.JSONField(help_text="Snapshot: name, address, tax_id, etc.")
    customer_snapshot = models.JSONField(help_text="Snapshot: name, email, address, etc.")
    tax_snapshot = models.JSONField(help_text="Snapshot: tax_mode, rates applied, etc.")
    items_snapshot = models.JSONField(help_text="List of services, pets, and prices covered by this invoice")
    
    # Technical Fields
    pdf_file = models.FileField(upload_to='invoices/%Y/%m/%d/', null=True, blank=True)
    transaction_reference = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
            models.Index(fields=['issued_at']),
        ]

    def __str__(self):
        return f"{self.invoice_number} ({self.status})"


class WaitlistEntry(models.Model):
    """Tier 3: Demand capture for fully booked slots (Rule 6)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField()
    owner = models.ForeignKey(PetOwnerProfile, on_delete=models.CASCADE)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    service_id = models.UUIDField()
    
    preferred_date = models.DateField()
    preferred_time_start = models.TimeField()
    preferred_time_end = models.TimeField()
    
    # Priority & Lifecycle
    is_vip = models.BooleanField(default=False) # Rule 6
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pending'),
        ('CONVERTED', 'Converted'),
        ('EXPIRED', 'Expired')
    ])
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_vip', 'created_at'] # Oldest first + VIP (Rule 6)


