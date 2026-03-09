import uuid
from django.db import models
from django.utils import timezone

class VisitGroup(models.Model):
    """
    Atomic unit for a multi-service cart. 
    Groups multiple BookingItems into a single conceptual visit.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(help_text="The clinic or provider where this visit takes place", db_index=True)
    pet_id = models.UUIDField(db_index=True)
    owner_id = models.UUIDField(db_index=True)
    
    idempotency_key = models.CharField(max_length=255, unique=True, help_text="To prevent duplicate bookings on retries")
    
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
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('NO_SHOW', 'No Show'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.UUIDField(db_index=True)
    
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='INR')
    
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Snapshots for header
    owner_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of owner details")
    address_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of the address at time of booking")
    
    # Payment Tracking
    payment_gateway = models.CharField(max_length=50, default='STRIPE')
    transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    checkout_session_url = models.URLField(max_length=1024, blank=True, null=True)

    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner_id', 'status']),
        ]

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class BookingItem(models.Model):
    """Individual bookable items inside a Booking"""
    
    ITEM_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
        ('NO_SHOW', 'No Show'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    visit_group = models.ForeignKey(VisitGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    # Target Info (Decoupled IDs)
    provider_id = models.UUIDField(help_text="UUID of the service provider")
    provider_auth_id = models.CharField(max_length=255, null=True, blank=True)
    assigned_employee_id = models.UUIDField(null=True, blank=True, help_text="ID of the assigned employee")
    resource_id = models.UUIDField(null=True, blank=True, help_text="ID of the assigned resource/facility")
    pet_id = models.UUIDField(db_index=True)
    owner_id = models.UUIDField(db_index=True)
    
    # Service Info
    service_id = models.UUIDField()
    facility_id = models.UUIDField()
    
    selected_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Comprehensive Snapshots
    pet_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of pet details")
    owner_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of owner details at item level")
    employee_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot of employee details")
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
            models.Index(fields=['assigned_employee_id', 'selected_time']),
            models.Index(fields=['resource_id', 'selected_time']),
            models.Index(fields=['pet_id', 'selected_time']),
            models.Index(fields=['provider_id', 'selected_time']),
            models.Index(fields=['visit_group']),
        ]

    def __str__(self):
        return f"Item {self.id} for Order {self.booking.id}"


class BookingStatusHistory(models.Model):
    """Audit trail for booking status changes"""
    
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


class SubscriptionPlan(models.Model):
    """Available subscription plans for providers to purchase"""
    
    BILLING_CYCLE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='MONTHLY')
    trial_days = models.IntegerField(default=0, help_text="Number of free trial days")
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=list, blank=True, help_text="List of feature names/strings included in the plan")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.price} {self.currency}/{self.billing_cycle})"


class ProviderSubscription(models.Model):
    """A provider's active or historical subscription"""

    STATUS_CHOICES = [
        ('TRIAL', 'Trial'),
        ('ACTIVE', 'Active'),
        ('PAST_DUE', 'Past Due'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_id = models.UUIDField(help_text="UUID of the provider organization", db_index=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    
    external_subscription_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID from Stripe/Razorpay")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['provider_id', 'status']),
            models.Index(fields=['end_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['provider_id'],
                condition=models.Q(status='ACTIVE'),
                name='unique_active_subscription_per_provider'
            )
        ]

    def __str__(self):
        return f"Subscription for Provider {self.provider_id} - {self.status}"


class SubscriptionPayment(models.Model):
    """Payment records for a subscription"""

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(ProviderSubscription, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    payment_gateway = models.CharField(max_length=50, blank=True, help_text="e.g. Stripe, Razorpay")
    transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    checkout_session_url = models.URLField(max_length=1024, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} for Sub {self.subscription.id} - {self.status}"
