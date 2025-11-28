# service_provider/models.py
import uuid
from django.db import models
from django.utils import timezone
import re
from django.core.exceptions import ValidationError
class VerifiedUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user_id = models.UUIDField(unique=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    permissions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "verified_users"

    def __str__(self):
        return f"{self.full_name or 'Unknown'} ({self.role})"

    @property
    def is_authenticated(self):
        """Required for Django/DRF authentication."""
        return True


# service_provider/models.py

class ServiceProvider(models.Model):
    """
    Core provider profile, created for each VerifiedUser via Kafka sync.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ✅ Link to VerifiedUser
    verified_user = models.OneToOneField(
        "service_provider.VerifiedUser",  # Model name for VerifiedUser
        on_delete=models.CASCADE,
        related_name="provider_profile",
        to_field="auth_user_id",  # Linking by auth_user_id from VerifiedUser
        db_column="verified_user_auth_id"
    )

    # Profile-specific data (No direct modification of personal data here)
    profile_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("active", "Active"), ("blocked", "Blocked")],
        default="pending",
    )

    avatar = models.ImageField(upload_to="provider_avatars/", null=True, blank=True)
    avatar_size = models.CharField(max_length=100, null=True, blank=True)

    is_fully_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.verified_user.full_name or 'Unknown'} ({self.profile_status})"


class BusinessDetails(models.Model):
    """
    Stores detailed business information for a service provider.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ✅ Link to VerifiedUser for traceability
    verified_user = models.ForeignKey(
        "service_provider.VerifiedUser",
        on_delete=models.CASCADE,
        related_name="business_records",
        to_field="auth_user_id",
        db_column="verified_user_auth_id"
    )

    # ✅ Link to ServiceProvider profile
    service_provider = models.OneToOneField(
        "service_provider.ServiceProvider",
        on_delete=models.CASCADE,
        related_name="business_details"
    )

    # ✅ Core Business Fields
    business_name = models.CharField(max_length=150, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_description = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    # ✅ Verification Fields
    is_business_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name or f"BusinessDetails-{self.id}"

    # ---------------- Validation ----------------
    def clean(self):
        """Custom validation for PAN and GSTIN fields."""
        super().clean()

        # Validate PAN format
        if self.pan_number and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', self.pan_number):
            raise ValidationError({"pan_number": "Invalid PAN format. Example: ABCDE1234F"})

        # Validate GST format
        if self.gst_number and not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', self.gst_number):
            raise ValidationError({"gst_number": "Invalid GSTIN format. Example: 27ABCDE1234F1ZV"})

        # If verified, set timestamp
        if self.is_business_verified and not self.verified_at:
            self.verified_at = timezone.now()

class DocumentVerification(models.Model):
    """
    Stores uploaded verification documents for a service provider.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ✅ Link to VerifiedUser for global traceability
    verified_user = models.ForeignKey(
        "service_provider.VerifiedUser",
        on_delete=models.CASCADE,
        related_name="document_records",
        to_field="auth_user_id",
        db_column="verified_user_auth_id"
    )

    # ✅ Link to ServiceProvider
    service_provider = models.OneToOneField(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    aadhar_card = models.FileField(upload_to="aadhar_docs/", null=True, blank=True)
    business_license = models.FileField(upload_to="licenses/", null=True, blank=True)
    pan_card = models.FileField(upload_to="pan_cards/", null=True, blank=True)
    gst_certificate = models.FileField(upload_to="gst_certificates/", null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    verified_by = models.CharField(max_length=100, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Documents of {self.service_provider.full_name}"


class VerificationWorkflow(models.Model):
    """
    Tracks verification progress (manual/auto) for each provider.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ✅ Link to VerifiedUser
    verified_user = models.ForeignKey(
        "service_provider.VerifiedUser",
        on_delete=models.CASCADE,
        related_name="workflow_records",
        to_field="auth_user_id",
        db_column="verified_user_auth_id"
    )

    # ✅ Link to ServiceProvider
    service_provider = models.OneToOneField(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="verification_workflow"
    )

    manual_verification = models.BooleanField(default=False)
    automated_verification = models.BooleanField(default=False)

    verified_stage = models.CharField(
        max_length=50,
        choices=[
            ("personal_pending", "Personal Info Pending"),
            ("business_pending", "Business Info Pending"),
            ("documents_pending", "Documents Pending"),
            ("verified", "Fully Verified"),
        ],
        default="personal_pending",
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workflow for {self.service_provider.full_name} - {self.verified_stage}"
    
    
    
    
    
    
    # =============================================================
    
    
class Document(models.Model):
    """
    Represents a single document type that can be required by a service type.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_name = models.CharField(max_length=150)  # e.g., "Business License", "Training Certificate"
    is_mandatory = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.document_name

class DocumentVerificationCategory(models.Model):
    """
    Defines required document types for each service category.
    Example: Vet -> License, Medical Certificate; Groomer -> Training Cert, Hygiene Cert.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=100)  # e.g., "grooming", "veterinary", "training"

    # Many-to-many relationship with Document model
    documents = models.ManyToManyField(Document, related_name="service_types")

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.service_type}"

class ProviderDocument(models.Model):
    """
    Stores actual uploaded files for each required document.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    verified_user = models.ForeignKey(
        "service_provider.VerifiedUser",
        on_delete=models.CASCADE,
        related_name="provider_documents",
        to_field="auth_user_id",
        db_column="verified_user_auth_id"
    )

    service_provider = models.ForeignKey(
        "service_provider.ServiceProvider",
        on_delete=models.CASCADE,
        related_name="uploaded_documents"
    )

    category = models.ForeignKey(
        DocumentVerificationCategory,
        on_delete=models.CASCADE,
        related_name="provider_docs"
    )

    file = models.FileField(upload_to="provider_documents/", null=True, blank=True)
    file_size = models.CharField(max_length=50, null=True, blank=True)

    verification_status = models.CharField(
        max_length=30,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )

    remarks = models.TextField(null=True, blank=True)
    verified_by = models.CharField(max_length=100, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.document_name} - {self.verification_status}"
class AutoVerificationLog(models.Model):
    """
    Logs automated verification responses (e.g., from GST, PAN, Aadhar APIs).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_document = models.ForeignKey(
        ProviderDocument,
        on_delete=models.CASCADE,
        related_name="verification_logs"
    )
    verification_source = models.CharField(max_length=100)  # e.g., "GST API", "Aadhar API"
    response_status = models.CharField(max_length=50)  # e.g., "success", "failed"
    response_data = models.JSONField(null=True, blank=True)
    verified_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.verification_source} - {self.response_status}"
