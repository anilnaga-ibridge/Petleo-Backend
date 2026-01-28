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

    def get_all_plan_capabilities(self):
        """
        Returns ALL capability keys derived from the user's purchased plan.
        This corresponds to the 'Upper Bound' of access.
        """
        # Avoid circular imports
        from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory, ProviderTemplateService
        
        # 1. Get Categories assigned in ProviderCapabilityAccess (The Plan)
        cat_ids = self.capabilities.filter(category_id__isnull=False).values_list('category_id', flat=True)
        
        # 2. Resolve to Linked Capabilities (e.g., 'Category: Pharmacy' -> 'VETERINARY_PHARMACY')
        linked_caps = set(ProviderTemplateCategory.objects.filter(
            super_admin_category_id__in=cat_ids
        ).exclude(linked_capability__isnull=True).values_list('linked_capability', flat=True))

        # 3. [FIX] Resolve Simple Services (Grooming, Daycare, etc.)
        # These services don't have categories, so we check for service-level access.
        service_ids = self.capabilities.filter(
            service_id__isnull=False, 
            category_id__isnull=True,
            can_view=True
        ).values_list('service_id', flat=True)
        
        SERVICE_CAPABILITY_MAP = {
            "Grooming": "GROOMING",
            "Daycare": "DAYCARE",
            "Training": "TRAINING",
            "Boarding": "BOARDING",
            "Walking": "WALKING",
            "Aquamation": "AQUAMATION",
            "Adoption": "ADOPTION",
        }
        
        if service_ids:
             # Look up service names
             service_names = ProviderTemplateService.objects.filter(
                 super_admin_service_id__in=service_ids
             ).values_list('display_name', flat=True)
             
             for name in service_names:
                 if name in SERVICE_CAPABILITY_MAP:
                     linked_caps.add(SERVICE_CAPABILITY_MAP[name])
        
        return linked_caps.union(
            set(self.dynamic_capabilities.filter(is_active=True).values_list('capability__key', flat=True))
        )


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


class Capability(models.Model):
    """
    Human-readable labels and descriptions for technical capability keys.
    """
    key = models.CharField(max_length=100, primary_key=True) # e.g. VETERINARY_VITALS
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    group = models.CharField(max_length=50, default="General") # e.g. Reception, Nursing, Doctor

    def __str__(self):
        return f"[{self.group}] {self.label}"


class ProviderRole(models.Model):
    """
    Provider-scoped roles (e.g., "Senior Nurse").
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="custom_roles"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_system_role = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "name")

    def __str__(self):
        return f"{self.name} ({self.provider})"


class ProviderRoleCapability(models.Model):
    """
    Maps ProviderRole to capability keys.
    """
    provider_role = models.ForeignKey(
        ProviderRole,
        on_delete=models.CASCADE,
        related_name="capabilities"
    )
    capability_key = models.CharField(max_length=100) # e.g. VETERINARY_VITALS

    class Meta:
        unique_together = ("provider_role", "capability_key")

    def __str__(self):
        return f"{self.provider_role.name} - {self.capability_key}"


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

    provider_role = models.ForeignKey(
        ProviderRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees"
    )

    # Denormalized fields for direct access
    full_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=50, default="employee")
    
    # Computed + Override permissions
    permissions_json = models.JSONField(default=dict, blank=True)
    
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

    # @deprecated - prevent new usage
    LEGACY_ROLE_MAP = {
        "receptionist": ["VETERINARY_CORE", "VETERINARY_VISITS"],
        "vitals staff": ["VETERINARY_CORE", "VETERINARY_VITALS"],
        "doctor": ["VETERINARY_CORE", "VETERINARY_VISITS", "VETERINARY_VITALS", "VETERINARY_PRESCRIPTIONS", "VETERINARY_LABS"],
        "lab tech": ["VETERINARY_CORE", "VETERINARY_LABS"],
        "pharmacy": ["VETERINARY_CORE", "VETERINARY_MEDICINE_REMINDERS"],
        "employee": ["VETERINARY_CORE"]
    }

    def get_final_permissions(self):
        """
        Calculate Employee Permissions.
        Rule: Effective Access = (Organization Plan Capabilities) ∩ (Employee Assigned Role)
        
        We STRICTLY enforce that an employee cannot have a permission that the Organization does not possess.
        """
        import logging
        logger = logging.getLogger(__name__)

        # 1. The Ceiling: Organization's Purchases (Upper Bound)
        org_caps = self.organization.verified_user.get_all_plan_capabilities()
        
        # 2. The Selection: Employee's Assigned Role
        role_capabilities = set()
        
        if self.provider_role:
            # Modern Path: Custom DB Role
            role_capabilities = set(
                self.provider_role.capabilities.values_list("capability_key", flat=True)
            )
        else:
            # Deprecated Path: Legacy Map
            # TODO: Migration script to create ProviderRoles for all employees
            legacy_key = (self.role or "employee").lower()
            role_capabilities = set(self.LEGACY_ROLE_MAP.get(legacy_key, []))
            
            # Log warning only if they are actually using capabilities beyond CORE
            if len(role_capabilities) > 1: 
                logger.warning(f"[DEPRECATION] Employee {self.auth_user_id} using LEGACY_ROLE_MAP for role '{legacy_key}'")

        # 3. The Intersection: Only allow what the Plan allows
        final_permissions = org_caps.intersection(role_capabilities)
        
        # 4. Core Access (Conditional)
        # Only grant VETERINARY_CORE if the user has other VETERINARY_* permissions
        # OR if it was explicitly captured in the intersection.
        has_vet_capabilities = any(cap.startswith("VETERINARY_") for cap in final_permissions)
        
        if has_vet_capabilities:
            final_permissions.add("VETERINARY_CORE")
            
        # Ensure basic provider access if needed, but do NOT force VETERINARY_CORE for Groomers.

        # 5. Apply Overrides (permissions_json) - RARE case
        overrides = self.permissions_json or {}
        add_overrides = set(overrides.get("ADD", []))
        remove_overrides = set(overrides.get("REMOVE", []))

        # IMPORTANT: Even 'ADD' overrides should technically be checked against Plan,
        # but for now we trust specific manual overrides.
        final_permissions.update(add_overrides)
        final_permissions.difference_update(remove_overrides)

        return list(final_permissions)


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


class FeatureModule(models.Model):
    """
    Synced from Super Admin. Controls UI modules.
    """
    key = models.CharField(max_length=100, unique=True)
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE, related_name="modules")
    
    name = models.CharField(max_length=255)
    route = models.CharField(max_length=255)
    api_pattern = models.CharField(max_length=255, blank=True, null=True)
    icon = models.CharField(max_length=100, default="tabler-box")
    sequence = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.key})"


class ProviderCapability(models.Model):
    """
    The source of truth for dynamic permissions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(VerifiedUser, on_delete=models.CASCADE, related_name="dynamic_capabilities")
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE)
    
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'capability')
        
    def __str__(self):
        return f"{self.user} -> {self.capability.key}"
