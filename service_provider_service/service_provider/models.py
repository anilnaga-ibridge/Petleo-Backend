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


    def __str__(self):
        return f"{self.verified_user.full_name or 'Unknown'} ({self.profile_status})"


class ProviderPermission(models.Model):
    """
    Stores permissions assigned to a provider.
    Synced from Super Admin Plans.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="provider_permissions"
    )
    permission_code = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("verified_user", "permission_code")

    def __str__(self):
        return f"{self.verified_user.email} - {self.permission_code}"


class AllowedService(models.Model):
    """
    Stores services that the provider is allowed to access/manage.
    Synced from Super Admin Plans.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="allowed_services"
    )
    service_id = models.UUIDField() # ID from Super Admin
    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=100, default="tabler-box")
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("verified_user", "service_id")

    def __str__(self):
        return f"{self.verified_user.email} - {self.name}"
