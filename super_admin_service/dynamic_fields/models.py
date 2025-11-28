# import uuid
# from django.db import models
# from django.utils import timezone
# from service_provider.models import VerifiedUser


# class ProviderFieldDefinition(models.Model):
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

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     target = models.CharField(max_length=20, choices=TARGET_CHOICES)

#     name = models.CharField(max_length=255)
#     label = models.CharField(max_length=255)

#     field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
#     is_required = models.BooleanField(default=False)

#     options = models.JSONField(default=list, blank=True)
#     order = models.IntegerField(default=0)

#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ["target", "order"]

#     def __str__(self):
#         return f"{self.target} - {self.label}"


# class ProviderFieldValue(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

#     verified_user = models.ForeignKey(
#         VerifiedUser,
#         on_delete=models.CASCADE,
#         to_field="auth_user_id",
#         related_name="provider_field_values"
#     )

#     field = models.ForeignKey(
#         ProviderFieldDefinition,
#         on_delete=models.CASCADE,
#         related_name="values"
#     )

#     value = models.JSONField(null=True, blank=True)

#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ("verified_user", "field")

#     def __str__(self):
#         return f"{self.verified_user.auth_user_id} - {self.field.label}"



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
