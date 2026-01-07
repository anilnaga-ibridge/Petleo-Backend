# from django.db import models
# import uuid
# from service_provider.models import VerifiedUser


# # ==========================================================
# # 1) PROVIDER FIELD VALUES
# # ==========================================================
# class ProviderFieldValue(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     verified_user = models.ForeignKey(
#         VerifiedUser,
#         on_delete=models.CASCADE,
#         to_field="auth_user_id",
#         related_name="dynamic_field_values"     # FIXED UNIQUE NAME
#     )
#     field_id = models.UUIDField() 
#     value = models.JSONField(null=True, blank=True)
#     metadata = models.JSONField(default=dict, blank=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ("verified_user", "field_id")

#     def __str__(self):
#         return f"{self.verified_user.auth_user_id} - {self.field_id}"


# # ==========================================================
# # 2) LOCAL FIELD DEFINITION
# # ==========================================================
# class LocalFieldDefinition(models.Model):
#     TARGET_CHOICES = [
#         ("individual", "Individual Provider"),
#         ("organization", "Organization Provider"),
#         ("employee", "Organization Employee"),
#     ]

#     FIELD_TYPES = [
#         ("text", "Text"),
#         ("number", "Number"),
#         ("textarea", "Textarea"),
#         ("dropdown", "Dropdown"),
#         ("multiselect", "Multiselect"),
#         ("file", "File Upload"),
#         ("date", "Date"),
#     ]

#     id = models.UUIDField(primary_key=True, editable=False)
#     target = models.CharField(max_length=20, choices=TARGET_CHOICES)
#     name = models.CharField(max_length=255)
#     label = models.CharField(max_length=255)
#     field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
#     is_required = models.BooleanField(default=False)
#     options = models.JSONField(default=list, blank=True)
#     order = models.IntegerField(default=0)
#     help_text = models.CharField(max_length=512, null=True, blank=True)
#     created_at = models.DateTimeField(null=True, blank=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ["target", "order", "name"]

#     def __str__(self):
#         return f"{self.target} → {self.label} ({self.name})"


# # ==========================================================
# # 3) LOCAL DOCUMENT DEFINITION
# # ==========================================================
# def provider_doc_upload_path(instance, filename):
#     return f"provider_docs/{instance.verified_user.auth_user_id}/{uuid.uuid4().hex}-{filename}"


# class LocalDocumentDefinition(models.Model):
#     TARGET_CHOICES = [
#         ("individual", "Individual Provider"),
#         ("organization", "Organization Provider"),
#         ("employee", "Organization Employee"),
#     ]

#     id = models.UUIDField(primary_key=True, editable=False)
#     target = models.CharField(max_length=20, choices=TARGET_CHOICES)
#     key = models.CharField(max_length=255)
#     label = models.CharField(max_length=255)
#     is_required = models.BooleanField(default=True)
#     allow_multiple = models.BooleanField(default=False)
#     allowed_types = models.JSONField(default=list, blank=True)
#     order = models.IntegerField(default=0)
#     help_text = models.CharField(max_length=512, null=True, blank=True)
#     created_at = models.DateTimeField(null=True, blank=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ["target", "order", "label"]

#     def __str__(self):
#         return f"{self.target} → {self.label}"


# # ==========================================================
# # 4) PROVIDER DOCUMENTS (UPLOADS)
# # ==========================================================
# class ProviderDocument(models.Model):
#     STATUS_CHOICES = [
#         ("pending", "Pending"),
#         ("approved", "Approved"),
#         ("rejected", "Rejected"),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     verified_user = models.ForeignKey(
#         VerifiedUser,
#         on_delete=models.CASCADE,
#         to_field="auth_user_id",
#         related_name="dynamic_documents"   # FIXED UNIQUE NAME
#     )
#     definition_id = models.UUIDField()
#     file = models.FileField(upload_to=provider_doc_upload_path)
#     filename = models.CharField(max_length=512)
#     content_type = models.CharField(max_length=128, null=True, blank=True)
#     size = models.BigIntegerField(default=0)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
#     notes = models.TextField(null=True, blank=True)
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ["-uploaded_at"]

#     def __str__(self):
#         return f"{self.verified_user.auth_user_id} • {self.filename}"
# provider_dynamic_fields/models.py




import uuid
from django.db import models
from service_provider.models import VerifiedUser


# PROFILE FIELD FILE UPLOAD
def provider_profile_field_upload_path(instance, filename):
    return f"provider_profile/{instance.verified_user.auth_user_id}/{uuid.uuid4().hex}-{filename}"


# 1) PROVIDER FIELD VALUES
class ProviderFieldValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="dynamic_field_values"
    )
    field_id = models.UUIDField()

    value = models.JSONField(null=True, blank=True)
    file = models.FileField(upload_to=provider_profile_field_upload_path, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("verified_user", "field_id")

    def __str__(self):
        return f"{self.verified_user.auth_user_id} - {self.field_id}"


# 2) LOCAL FIELD DEFINITIONS
class LocalFieldDefinition(models.Model):
    TARGET_CHOICES = [
        ("individual", "Individual Provider"),
        ("organization", "Organization Provider"),
        ("employee", "Organization Employee"),
    ]

    FIELD_TYPES = [
        ("text", "Text"),
        ("number", "Number"),
        ("textarea", "Textarea"),
        ("dropdown", "Dropdown"),
        ("multiselect", "Multiselect"),
        ("file", "File Upload"),
        ("date", "Date"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.CharField(max_length=20, choices=TARGET_CHOICES)
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)
    help_text = models.CharField(max_length=512, null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target", "order", "name"]


# 3) DOCUMENT DEFINITIONS
def provider_doc_upload_path(instance, filename):
    return f"provider_docs/{instance.verified_user.auth_user_id}/{uuid.uuid4().hex}-{filename}"


class LocalDocumentDefinition(models.Model):
    TARGET_CHOICES = [
        ("individual", "Individual Provider"),
        ("organization", "Organization Provider"),
        ("employee", "Organization Employee"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.CharField(max_length=20, choices=TARGET_CHOICES)
    key = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    is_required = models.BooleanField(default=True)
    allow_multiple = models.BooleanField(default=False)
    allowed_types = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)
    help_text = models.CharField(max_length=512, null=True, blank=True)


# 4) PROVIDER DOCUMENTS
class ProviderDocument(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="dynamic_documents"
    )

    definition_id = models.UUIDField()
    file = models.FileField(upload_to=provider_doc_upload_path)
    filename = models.CharField(max_length=512)
    content_type = models.CharField(max_length=128, null=True, blank=True)
    size = models.BigIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ==========================================================
# 5) PROVIDER CRUD MODELS (Isolated from SuperAdmin)
# ==========================================================

class ProviderCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="provider_categories",
        null=True, blank=True
    )
    service_id = models.CharField(max_length=255, null=True, blank=True)  # Stored as string ID
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        # unique_together = ("provider", "service_id", "name")

    def __str__(self):
        return f"{self.name} ({self.provider.full_name})"


class ProviderFacility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="provider_facilities",
        null=True, blank=True
    )
    category = models.ForeignKey(
        ProviderCategory,
        on_delete=models.CASCADE,
        related_name="facilities"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class ProviderPricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="provider_pricing",
        null=True, blank=True
    )
    service_id = models.CharField(max_length=255, null=True, blank=True)
    category_id = models.CharField(max_length=255, null=True, blank=True) # Can be ProviderCategory ID or SuperAdmin Category ID
    
    # Optional link to specific facility
    facility = models.ForeignKey(
        ProviderFacility,
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True,
        blank=True
    )
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50, help_text="e.g. per_hour, per_day, fixed")
    description = models.TextField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.price} - {self.duration}m ({self.provider.full_name})"


# ==========================================================
# 6) PROVIDER TEMPLATE MODELS (Synced from SuperAdmin)
# ==========================================================

class ProviderTemplateService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Original SuperAdmin ID
    super_admin_service_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    icon = models.CharField(max_length=255, default="tabler-box")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name


class ProviderTemplateCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    super_admin_category_id = models.CharField(max_length=255, unique=True)
    service = models.ForeignKey(
        ProviderTemplateService,
        on_delete=models.CASCADE,
        related_name="categories"
    )
    name = models.CharField(max_length=255)
    linked_capability = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Template)"


class ProviderTemplateFacility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    super_admin_facility_id = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(
        ProviderTemplateCategory,
        on_delete=models.CASCADE,
        related_name="facilities"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Template)"


class ProviderTemplatePricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    super_admin_pricing_id = models.CharField(max_length=255, unique=True)
    
    service = models.ForeignKey(
        ProviderTemplateService,
        on_delete=models.CASCADE,
        related_name="pricing_rules"
    )
    category = models.ForeignKey(
        ProviderTemplateCategory,
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True, blank=True
    )
    facility = models.ForeignKey(
        ProviderTemplateFacility,
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True, blank=True
    )
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ==========================================================
# 7) PROVIDER CAPABILITY ACCESS (Synced from SuperAdmin)
# ==========================================================
class ProviderCapabilityAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="capabilities"
    )
    plan_id = models.CharField(max_length=255) # Reference to SuperAdmin Plan ID
    
    # References to SuperAdmin IDs (stored as strings)
    service_id = models.CharField(max_length=255, null=True, blank=True)
    category_id = models.CharField(max_length=255, null=True, blank=True)
    facility_id = models.CharField(max_length=255, null=True, blank=True)
    pricing_id = models.CharField(max_length=255, null=True, blank=True)
    
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "plan_id", "service_id", "category_id", "facility_id", "pricing_id")

    def __str__(self):
        return f"{self.user.email} - {self.service_id}/{self.category_id}"
