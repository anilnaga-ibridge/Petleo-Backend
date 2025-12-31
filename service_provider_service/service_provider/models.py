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
    
    # Rich permission data synced from Super Admin
    service_id = models.CharField(max_length=100, null=True, blank=True)
    service_name = models.CharField(max_length=255, null=True, blank=True)
    service_icon = models.CharField(max_length=100, default="tabler-box")
    
    category_id = models.CharField(max_length=100, null=True, blank=True)
    category_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Boolean flags
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    
    # Facilities (stored as JSON since we don't have a Facility model here yet)
    facilities = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("verified_user", "service_id", "category_id")

    def __str__(self):
        return f"{self.verified_user.email} - {self.service_name} / {self.category_name}"


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


class OrganizationEmployee(models.Model):
    """
    Represents an employee belonging to an organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user_id = models.UUIDField(unique=True)  # The employee's auth ID
    
    organization = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="employees"
    )

    # Denormalized fields for direct access
    full_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=50, default="employee")
    
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("ACTIVE", "Active"), ("DISABLED", "Disabled")],
        default="PENDING"
    )
    
    created_by = models.UUIDField()  # Auth ID of the creator
    joined_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # Soft delete
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Employee {self.auth_user_id} of {self.organization}"


class ProviderSubscription(models.Model):
    """
    Tracks the local validity of a provider's plan.
    Synced from Super Admin via Kafka.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    plan_id = models.CharField(max_length=255)
    billing_cycle_id = models.CharField(max_length=255, null=True, blank=True)
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.verified_user.email} - {self.plan_id} ({'Active' if self.is_active else 'Inactive'})"
