


# users/models.py
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings

class Permission(models.Model):
    service_name = models.CharField(max_length=100, default='system')
    capability_key = models.CharField(max_length=100, unique=True, default='system.default')
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.service_name} - {self.capability_key}"

class Role(models.Model):
    clinic_id = models.UUIDField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=50, default='New Role')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    class Meta:
        # A clinic can't have two roles with the same exact name
        unique_together = ('clinic_id', 'name')

    def __str__(self):
        return f"{self.name} (Clinic: {self.clinic_id})"

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} -> {self.permission.capability_key}"


# class User(AbstractUser):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     username = models.CharField(max_length=150, unique=True)  # already from AbstractUser
#     phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
#     email = models.EmailField(unique=True, null=True, blank=True)
#     full_name = models.CharField(max_length=100, null=True, blank=True)
#     role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
#     token_version = models.IntegerField(default=0)

#     # --- PIN fields ---
#     pin_hash = models.CharField(max_length=255, null=True, blank=True)  # hashed PIN
#     pin_set_at = models.DateTimeField(null=True, blank=True)            # when PIN was set
#     last_pin_login = models.DateTimeField(null=True, blank=True)        # last time PIN was used to login

#     # optional: track last OTP login for auditing
#     last_otp_login = models.DateTimeField(null=True, blank=True)

#     USERNAME_FIELD = 'username'
#     REQUIRED_FIELDS = []

#     def has_permission(self, codename):
#         if not self.role:
#             return False
#         return self.role.permissions.filter(codename=codename).exists()

#     def __str__(self):
#         return self.username or str(self.id)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    token_version = models.IntegerField(default=0)

    # PIN fields
    pin_hash = models.CharField(max_length=255, null=True, blank=True)
    pin_length = models.IntegerField(default=4, null=True, blank=True) # New field to store PIN length
    pin_set_at = models.DateTimeField(null=True, blank=True)
    pin_expires_at = models.DateTimeField(null=True, blank=True)
    last_pin_login = models.DateTimeField(null=True, blank=True)

    # OTP login optional
    last_otp_login = models.DateTimeField(null=True, blank=True)

    # Staff Management
    clinic_id = models.UUIDField(null=True, blank=True, db_index=True) # Primary Clinic/Tenant
    organization_id = models.UUIDField(null=True, blank=True) # Legacy/Alternative
    status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('ACTIVE', 'Active'), ('DISABLED', 'Disabled')],
        default='PENDING'
    )

    # ⭐ New field for inactivity lock feature
    last_active_at = models.DateTimeField(null=True, blank=True)

    # 🖼️ Avatar field for cross-service sync
    avatar_url = models.URLField(max_length=500, null=True, blank=True)

    # ⭐ New field for verification tracking
    verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def has_permission(self, capability_key, action='view'):
        # In the new RBAC architecture, we should check UserRole -> Role -> RolePermission
        # However, to preserve performance, this will usually be checked via decorators grabbing JWT cache.
        # This is a fallback database query method.
        if not hasattr(self, 'clinic_id') or not self.clinic_id:
            return False
            
        try:
            user_role = UserRole.objects.get(user=self, clinic_id=self.clinic_id)
            rp = RolePermission.objects.get(role=user_role.role, permission__capability_key=capability_key)
            if action == 'view': return rp.can_view
            elif action == 'create': return rp.can_create
            elif action == 'edit': return rp.can_edit
            elif action == 'delete': return rp.can_delete
        except (UserRole.DoesNotExist, RolePermission.DoesNotExist):
            return False
        return False

    def __str__(self):
        return self.username or str(self.id)

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_assignments')
    clinic_id = models.UUIDField(db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'clinic_id') # A user has ONE role per clinic

    def __str__(self):
        return f"{self.user.username} - {self.role.name} (Clinic: {self.clinic_id})"

class OTP(models.Model):
    PURPOSE_CHOICES = [
        ('register', 'Register'),
        ('login', 'Login'),
        ('verify', 'Verify'),
        ('auto_verify_login', 'AutoVerifyLogin'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES, default='login')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'purpose']),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at


class StoredRefreshToken(models.Model):
    """
    Opaque refresh tokens stored hashed for rotation and revocation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    user_agent = models.CharField(max_length=256, null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at




class EmailTemplate(models.Model):
    TEMPLATE_TYPES = (
        ("automatic", "Automatic"),
        ("manual", "Manual"),
    )

    ROLES = (
        ("admin", "Admin"),
        ("organization", "Organization"),
        ("individual", "Individual"),
        ("all", "All Users"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=50, choices=ROLES)
    type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, default="manual")
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    is_default = models.BooleanField(default=False)  # selected automatic template for the role
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.role} - {self.type})"

    def save(self, *args, **kwargs):
        # Ensure only ONE default automatic template exists per role
        if self.is_default and self.type == "automatic":
            EmailTemplate.objects.filter(
                role=self.role,
                type="automatic",
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)