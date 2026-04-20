
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility


class BillingCycleConfig(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="e.g. MONTHLY")
    display_name = models.CharField(max_length=100, help_text="e.g. Monthly")
    duration_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name


class Plan(models.Model):
    class TargetType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        ORGANIZATION = "ORGANIZATION", "Organization"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    target_type = models.CharField(
        max_length=20, 
        choices=TargetType.choices,
        default=TargetType.ORGANIZATION
    )
    
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    features = models.JSONField(default=list, blank=True, null=True)

    # Pricing & Billing
    billing_cycle = models.CharField(
        max_length=50,
        default="MONTHLY",
        help_text="Code from BillingCycleConfig"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default="INR")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Plan.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.target_type} - {self.billing_cycle})"


class SubscriptionPlan(models.Model):
    """
    Modern Subscription Plan model for multi-service licensing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    # Tiering
    tier = models.CharField(
        max_length=20, 
        choices=[('BASIC', 'Basic'), ('PRO', 'Pro'), ('ENTERPRISE', 'Enterprise')],
        default='BASIC'
    )
    
    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='INR')
    
    # Limits & Caps (JSON for flexibility)
    capabilities = models.JSONField(
        default=dict, 
        help_text="Feature flags: {'veterinary_vitals': true, 'max_doctors': 5...}"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.tier})"


class PlanCapability(models.Model):
    """
    Defines what a Plan allows a user to do.
    Stored as normalized rows: Plan + Service + Category + (Optional Facility) -> Permissions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="capabilities")

    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)

    # Granular Controls
    limits = models.JSONField(default=dict, blank=True, help_text="e.g. {'max_bookings': 100}")
    permissions = models.JSONField(default=dict, blank=True, help_text="e.g. {'can_create': true, 'online_consult': true}")

    class Meta:
        unique_together = ("plan", "service", "category", "facility")

    def __str__(self):
        svc = self.service.display_name if self.service else "NoService"
        cat = self.category.name if self.category else "NoCategory"
        fac = self.facility.name if self.facility else "AllFacilities"
        return f"{self.plan.title} - {svc} > {cat} > {fac}"


class Coupon(models.Model):
    """
    Coupon / Discount management for Plans.
    """
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percent"),
        ("fixed", "Fixed Amount"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=6, decimal_places=2)

    max_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    applicable_roles = models.JSONField(default=list, blank=True, null=True)
    applies_to_plans = models.ManyToManyField(Plan, blank=True)

    min_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self, now=None):
        now = now or timezone.now()
        if not self.is_active:
            return False
        if self.end_date and self.end_date < now:
            return False
        if self.used_count >= self.max_uses:
            return False
        return True

    def clean(self):
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValidationError("Percent discount cannot exceed 100%.")

    def __str__(self):
        return f"{self.code} ({self.discount_type})"


class PurchasedPlan(models.Model):
    """
    When a user buys a plan this records the purchase and billing cycle.
    Status logic:
    - PENDING: After purchase but before payment confirmation.
    - ACTIVE: After payment success (permissions granted).
    - EXPIRED: After end_date.
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchased_plans")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="purchases")
    
    billing_cycle = models.CharField(
        max_length=50,
        default="MONTHLY"
    )

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)  # Set to True only after PAID
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    # Reconciliation fields
    is_legacy_reconciled = models.BooleanField(default=False)
    entitlement_source = models.CharField(
        max_length=50, 
        choices=[('BILLING', 'Billing'), ('MIGRATION', 'Migration')], 
        default='BILLING'
    )
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.plan.title} ({self.status})"


class ProviderPlanCapability(models.Model):

    """
    Actual permissions assigned to a user (provider) after purchasing a plan.
    Copied from PlanCapability templates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_capabilities")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="assigned_capabilities")

    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True)

    # Granular Controls (Copied from PlanCapability)
    limits = models.JSONField(default=dict, blank=True)
    permissions = models.JSONField(default=dict, blank=True)

    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "plan", "service", "category", "facility")

    def __str__(self):
        return f"{self.user} - {self.plan.title} ({self.service} / {self.category})"


class TaxConfiguration(models.Model):
    """
    Global tax rate administration.
    """
    key = models.CharField(max_length=50, unique=True, help_text="e.g. GST_STANDARD")
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="e.g. 18.00")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.key}: {self.rate}%"


class BillingSequence(models.Model):
    """
    Atomic sequential counter for invoice numbering.
    Use select_for_update() on the record for a specific year.
    """
    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Year {self.year}: Last #{self.last_number}"


class Invoice(models.Model):
    """
    Production-grade B2B Invoice with immutable snapshots.
    """
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("ISSUED", "Issued"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
        ("VOID", "Void"),
    ]

    TAX_MODE_CHOICES = [
        ("INTRA_STATE", "Intra-State (CGST + SGST)"),
        ("INTER_STATE", "Inter-State (IGST)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Relationships
    purchased_plan = models.OneToOneField(PurchasedPlan, on_delete=models.CASCADE, related_name="invoice")
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")

    # Immutable Snapshots - Buyer (Captured from ProviderBillingProfile)
    buyer_name = models.CharField(max_length=255)
    buyer_address = models.TextField()
    buyer_gstin = models.CharField(max_length=15, blank=True, null=True)
    buyer_state_code = models.CharField(max_length=10)

    # Immutable Snapshots - Seller (Captured from settings)
    seller_name = models.CharField(max_length=255)
    seller_address = models.TextField()
    seller_gstin = models.CharField(max_length=15)
    seller_state_code = models.CharField(max_length=10)

    # Immutable Snapshots - Tax
    tax_mode = models.CharField(max_length=20, choices=TAX_MODE_CHOICES)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Financials
    currency = models.CharField(max_length=3, default="INR")
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Status & Logistics
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ISSUED")
    coupon_code_used = models.CharField(max_length=50, blank=True, null=True)
    
    # Payment Details
    payment_provider = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_payload_json = models.JSONField(default=dict, blank=True)

    # File storage
    pdf_file = models.FileField(upload_to="invoices/%Y/%m/", null=True, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    issued_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["issued_at"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.total_amount} {self.currency}"


class BillingAuditLog(models.Model):
    """
    Settlement audit logs for critical billing events.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="audit_logs")
    event_type = models.CharField(max_length=50, help_text="e.g. invoice.paid, payment.verified")
    description = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.invoice.invoice_number}"


class LegacyEntitlementRecovery(models.Model):
    """
    Audit-safe record of a legacy PurchasedPlan brought into the modern sync system.
    Ensures that access is restored without fabricating tax invoices.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchased_plan = models.OneToOneField(
        PurchasedPlan, 
        on_delete=models.CASCADE, 
        related_name="legacy_recovery"
    )
    
    recovered_at = models.DateTimeField(default=timezone.now)
    migration_record_number = models.CharField(max_length=50, unique=True)
    
    # Audit details
    administered_by = models.CharField(max_length=255, default="SYSTEM_SYNC_RECOVERY")
    reason = models.TextField(blank=True, default="Automatic production-safe reconciliation")
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "legacy_entitlement_recovery"
        verbose_name_plural = "Legacy Entitlement Recoveries"

    def __str__(self):
        return f"Recovery {self.migration_record_number} for {self.purchased_plan}"


class MigrationRecordSequence(models.Model):
    """
    Atomic counter for Migration Records (MR-YYYY-000001).
    """
    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"MR Year {self.year}: Last #{self.last_number}"