



import uuid
from django.db import models
from django.utils import timezone

class ProviderFieldDefinition(models.Model):
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
    name = models.CharField(max_length=255)   # machine name, e.g. "business_license_no"
    label = models.CharField(max_length=255)  # UI label
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)  # for dropdown/multi
    order = models.IntegerField(default=0)
    help_text = models.CharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target", "order", "name"]

    def __str__(self):
        return f"{self.target} — {self.label} ({self.name})"



import uuid
from django.db import models
from django.utils import timezone

class ProviderDocumentDefinition(models.Model):
    TARGET_CHOICES = [
        ("individual", "Individual Provider"),
        ("organization", "Organization Provider"),
        ("employee", "Organization Employee"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.CharField(max_length=20, choices=TARGET_CHOICES)

    key = models.CharField(max_length=255)       # machine key (e.g. "id_proof", "business_certificate")
    label = models.CharField(max_length=255)     # UI label ("ID Proof", "GST Certificate")
    
    is_required = models.BooleanField(default=True)
    allow_multiple = models.BooleanField(default=False)

    allowed_types = models.JSONField(default=list)  
    # Example: ["image/png", "image/jpeg", "application/pdf"]

    order = models.IntegerField(default=0)
    help_text = models.CharField(max_length=512, blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target", "order", "label"]

    def __str__(self):
        return f"{self.target} — {self.label} ({self.key})"


class ProviderDocumentVerification(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user_id = models.UUIDField()  # auth_user_id from Service Provider
    document_id = models.UUIDField()  # ID of the document in Service Provider DB
    
    file_url = models.URLField(max_length=1024, blank=True, null=True)
    filename = models.CharField(max_length=512, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Doc {self.document_id} ({self.status})"
