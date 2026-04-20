

# super_admin/models.py
import uuid
from django.db import models
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.utils import timezone

STATUS_CHOICES = [
    ('active', 'Active'),
    ('pending', 'Pending'),
    ('inactive', 'Inactive'),
    ('blocked', 'Blocked'),
]

class SuperAdminManager(BaseUserManager):
    def create_superadmin(self, email, contact, password=None):
        if not email:
            raise ValueError("SuperAdmins must have an email address")
        if not contact:
            raise ValueError("SuperAdmins must have a contact number")

        superadmin = self.model(
            email=self.normalize_email(email),
            contact=contact
        )
        superadmin.set_password(password)
        superadmin.save(using=self._db)
        return superadmin


class SuperAdmin(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXED 👇 (UUIDField → CharField)
    auth_user_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    email = models.EmailField(max_length=255, unique=True)
    contact = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=True)
    user_role = models.CharField(max_length=50, default='Admin', null=True)
    is_super_admin = models.BooleanField(default=True)

    activity_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )

    objects = SuperAdminManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['contact']

    def __str__(self):
        return self.email



class VerifiedUser(models.Model):
    """
    Stores verified users coming from the Auth Service (via Kafka).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXED 👇 (UUIDField → CharField)
    auth_user_id = models.CharField(max_length=50, unique=True)

    full_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    permissions = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "verified_users"
        indexes = [
            models.Index(fields=["auth_user_id"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.full_name or 'Unknown'} ({self.role})"



class ActiveAdminProfileManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.name



class AdminProfile(models.Model):
    """
    Admin profile extending VerifiedUser with additional info.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXED: VerifiedUser.auth_user_id is CharField now
    verified_user = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="admin_profile",
        to_field="auth_user_id",       # FK uses CharField auth_user_id
        db_column="verified_user_auth_id"
    )

    department = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to="admin_profiles/", blank=True, null=True)

    is_deleted = models.BooleanField(default=False)

    activity_status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("suspended", "Suspended"),
        ],
        default="active",
    )

    permissions = models.ManyToManyField(Permission, blank=True, related_name="admins")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveAdminProfileManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "admin_profiles"

    def __str__(self):
        return f"Admin: {self.verified_user.email}"

class GlobalBranding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_name = models.CharField(max_length=255, default="PetLeo")
    primary_color = models.CharField(max_length=7, default="#7367F0")
    secondary_color = models.CharField(max_length=7, default="#CE9FFC")
    logo = models.ImageField(upload_to="branding/logos/", null=True, blank=True)
    favicon = models.ImageField(upload_to="branding/favicons/", null=True, blank=True)
    hide_app_name = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Global Branding - {self.app_name}"

class ProviderBillingProfile(models.Model):
    """
    Stores billing and tax information for a provider organization/individual.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="billing_profile",
        to_field="auth_user_id"
    )

    legal_name = models.CharField(max_length=255, help_text="Legal business name for invoices")
    billing_address = models.TextField(help_text="Full registered address")
    billing_state = models.CharField(max_length=100)
    billing_state_code = models.CharField(max_length=10, help_text="e.g. KA, MH")
    billing_gstin = models.CharField(max_length=15, blank=True, null=True)

    # Reconciliation fields
    is_incomplete = models.BooleanField(default=False)
    source = models.CharField(
        max_length=50, 
        choices=[('ORGANIC', 'Organic'), ('RECOVERY', 'Recovery')], 
        default='ORGANIC'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Billing: {self.legal_name} ({self.verified_user.email})"


class AnalyticsSnapshot(models.Model):
    """
    Cached snapshots for high-performance analytics.
    Avoids heavy DB aggregation on every request.
    """
    snapshot_key = models.CharField(max_length=100, db_index=True)
    period_date = models.DateField(null=True, blank=True, help_text="e.g. 2026-04-17 for daily snapshots")
    data_json = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    version = models.CharField(max_length=20, default="1.0")

    class Meta:
        db_table = "analytics_snapshots"
        unique_together = ("snapshot_key", "period_date", "version")
        indexes = [
            models.Index(fields=["snapshot_key", "period_date"]),
        ]

    def __str__(self):
        return f"Snapshot: {self.snapshot_key} ({self.period_date or 'Global'}) - v{self.version}"

    @property
    def is_stale(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
