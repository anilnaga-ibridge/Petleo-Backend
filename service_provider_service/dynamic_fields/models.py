from django.db import models
import uuid
# Create your models here.
from service_provider.models import VerifiedUser
# Provider's answers (values)
class ProviderFieldValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        to_field="auth_user_id",
        related_name="provider_field_values"
    )
    field_id = models.UUIDField()  # references ProviderFieldDefinition.id in SuperAdmin
    value = models.JSONField(null=True, blank=True)  # supports scalar, list, file metadata etc.
    metadata = models.JSONField(default=dict, blank=True)  # optional (e.g., uploaded file details)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("verified_user", "field_id")

    def __str__(self):
        return f"{self.verified_user.auth_user_id} - {self.field_id}"
    
class LocalFieldDefinition(models.Model):
    """
    This is the local copy of SuperAdmin -> ProviderFieldDefinition.
    It is synced through Kafka consumer.
    """

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

    # → Must match ID from SuperAdmin model EXACTLY
    id = models.UUIDField(primary_key=True, editable=False)

    target = models.CharField(max_length=20, choices=TARGET_CHOICES)

    name = models.CharField(max_length=255)      # business_license_no
    label = models.CharField(max_length=255)     # UI label
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)

    options = models.JSONField(default=list, blank=True)   # for dropdown/multi
    order = models.IntegerField(default=0)

    help_text = models.CharField(max_length=512, null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target", "order", "name"]

    def __str__(self):
        return f"{self.target} → {self.label} ({self.name})"