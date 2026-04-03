# service_provider/models.py
import uuid
from django.db import models
from django.utils import timezone
import re
import logging
from django.core.exceptions import ValidationError
from django.core.cache import cache
from .models_scheduling import EmployeeWeeklySchedule, EmployeeLeave, EmployeeBlockTime
from .models_kafka import KafkaProcessedEvent, KafkaDeadLetterQueue

logger = logging.getLogger(__name__)
class VerifiedUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user_id = models.UUIDField(unique=True)
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

    def __str__(self):
        return f"{self.full_name or 'Unknown'} ({self.role})"

    @property
    def is_authenticated(self):
        """Required for Django/DRF authentication."""
        return True

    def get_all_plan_capabilities(self):
        """
        Returns ALL capability keys derived from the user's purchased plan.
        Updated: Now returns granular CRUD keys (VIEW, CREATE, EDIT, DELETE) 
        for every base capability to unify owner and employee permission formats.
        """
        # Avoid circular imports
        from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateCategory, ProviderTemplateService
        
        # 1. Get Categories assigned in ProviderCapabilityAccess (The Plan)
        cat_ids = self.capabilities.filter(category_id__isnull=False).values_list('category_id', flat=True)
        
        # 2. Resolve to Category Keys (e.g., 'Category: Pharmacy' -> 'VETERINARY_PHARMACY')
        cat_qs = ProviderTemplateCategory.objects.filter(super_admin_category_id__in=cat_ids)
        base_caps = set(cat_qs.exclude(category_key__isnull=True).exclude(category_key='').values_list('category_key', flat=True))
        
        # [FIX] Also include category names as capabilities if they look like capability keys
        # This fixes the issue where category_key is null but the name itself is 'VETERINARY_VISITS'
        for cat in cat_qs.filter(category_key__isnull=True) | cat_qs.filter(category_key=''):
            if cat.name and cat.name.isupper() and '_' in cat.name:
                base_caps.add(cat.name)

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
            "Day care": "DAY_CARE",
            "DAY_CARE": "DAY_CARE",
            "Training": "TRAINING",
            "Boarding": "BOARDING",
            "Basic Boarding": "BOARDING",
            "Walking": "WALKING",
            "Aquamation": "AQUAMATION",
            "Adoption": "ADOPTION",
            "Veterinary": "VETERINARY_CORE",
            "Veterinary Management": "VETERINARY_CORE",
            "VETERINARY": "VETERINARY_CORE",
            "SYSTEM_ADMIN": "SYSTEM_ADMIN_CORE",
            "System Management": "SYSTEM_ADMIN_CORE",
        }
        
        if service_ids:
             # Look up service names
             service_meta = ProviderTemplateService.objects.filter(
                 super_admin_service_id__in=service_ids
             ).values_list('name', 'display_name')
             
             for name, display_name in service_meta:
                 if name in SERVICE_CAPABILITY_MAP:
                     base_caps.add(SERVICE_CAPABILITY_MAP[name])
                 elif display_name in SERVICE_CAPABILITY_MAP:
                     base_caps.add(SERVICE_CAPABILITY_MAP[display_name])
        
        # 4. [FIX] Add VETERINARY_CORE if any clinical-module category keys are present.
        # Clinical plans (e.g., Platinum) include categories like PHARMACY, VISITS, LABS etc.
        # The plan purchases these via category_id, so they appear in base_caps as their category_key.
        # Without this block, VETERINARY_CORE is never triggered and the Veterinary Hub is hidden.
        CLINICAL_MODULE_KEYS = {
            'PHARMACY', 'VISITS', 'LABS', 'DOCTOR_STATION', 'VETERINARY_ASSISTANT',
            'PATIENTS', 'OFFLINE_VISITS', 'MEDICINE_REMINDERS', 'CLINIC_SETTINGS',
            'METADATA_MANAGEMENT', 'BOARDING_BASIC', 'VETERINARY_CORE',
        }
        has_vet_capabilities = (
            any(cap.startswith('VETERINARY_') for cap in base_caps) or
            bool(base_caps & CLINICAL_MODULE_KEYS)
        )
        if has_vet_capabilities:
            base_caps.add('VETERINARY_CORE')
            
        # 5. [FIX] Expand VETERINARY_CORE to all sub-capabilities
        # If the org bought "Veterinary Management", they inherently have access to all modules,
        # which permits the granular Role-Based Access Control to filter these out for employees.
        if 'VETERINARY_CORE' in base_caps:
            base_caps.update([
                'VETERINARY_DOCTOR',
                'VETERINARY_VISITS',
                'VETERINARY_VITALS',
                'VETERINARY_LABS',
                'VETERINARY_PRESCRIPTIONS',
                'VETERINARY_PHARMACY',
                'VETERINARY_SCHEDULE',
                'VETERINARY_ONLINE_CONSULT',
                'VETERINARY_OFFLINE_VISIT',
                'VETERINARY_ADMIN_SETTINGS',
                'VETERINARY_METADATA',
                'VETERINARY_MEDICINE_REMINDERS',
                'VETERINARY_CHECKOUT',
                'VETERINARY_PATIENTS',
            ])
            
        # 6. [NEW] Expand SYSTEM_ADMIN_CORE to all sub-capabilities
        # NOTE: Owners (Organization/Individual) always get management modules as baseline platform features.
        system_keys = ['EMPLOYEE_MANAGEMENT', 'ROLE_MANAGEMENT', 'CUSTOMER_BOOKING', 'CLINIC_MANAGEMENT']
        
        is_owner = self.role and self.role.upper() in ['ORGANIZATION', 'INDIVIDUAL', 'SUPER_ADMIN']
        
        if is_owner or 'SYSTEM_ADMIN_CORE' in base_caps or any(k in base_caps for k in system_keys):
            # [STRICT] If role is INDIVIDUAL, remove management-heavy features (staffing)
            if self.role and self.role.upper() == 'INDIVIDUAL':
                system_keys = [k for k in system_keys if k not in ['ROLE_MANAGEMENT', 'EMPLOYEE_MANAGEMENT', 'CLINIC_MANAGEMENT']]
            
            base_caps.update(system_keys)

        # 7. Merge with dynamic capabilities
        dynamic_caps = set(self.dynamic_capabilities.filter(is_active=True).values_list('capability__key', flat=True))
        base_caps.update(dynamic_caps)

        # 8. 🔥 [ENHANCEMENT] Explode to Granular CRUD Keys
        # Owners inherit full permissions for everything their plan allows.
        granular_perms = set()
        for cap in base_caps:
            if any(cap.endswith(sfx) for sfx in ['_VIEW', '_CREATE', '_EDIT', '_DELETE']):
                granular_perms.add(cap)
            else:
                granular_perms.update([
                    f"{cap}_VIEW", f"{cap}_CREATE", f"{cap}_EDIT", f"{cap}_DELETE",
                    cap # Also include the base key for easier checks in views
                ])
        
        print(f"🎯 [RBAC] Generated permissions for {self.email} (Role: {self.role}): {len(granular_perms)} keys")
        if "ROLE_MANAGEMENT_VIEW" not in granular_perms:
            print(f"   ⚠️ [RBAC] ROLE_MANAGEMENT_VIEW MISSING! Role: {self.role}")
            print(f"   📊 Base Caps: {sorted(list(base_caps))}")
            print(f"   👤 User: {self.email} (ID: {self.auth_user_id})")
        
        return granular_perms



class ProviderAvailability(models.Model):
    """Weekly working hours for individual providers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "service_provider.ServiceProvider",
        on_delete=models.CASCADE,
        related_name="individual_availability"
    )
    day_of_week = models.IntegerField(help_text="0-6 (Mon-Sun)")
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("provider", "day_of_week")
        ordering = ["day_of_week", "start_time"]



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
    PROVIDER_TYPE_CHOICES = (
        ("INDIVIDUAL", "Individual"),
        ("ORGANIZATION", "Organization"),
    )

    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPE_CHOICES,
        default="INDIVIDUAL"
    )

    profile_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("active", "Active"), ("blocked", "Blocked")],
        default="pending",
    )

    avatar = models.ImageField(upload_to="provider_avatars/", null=True, blank=True)
    avatar_size = models.CharField(max_length=100, null=True, blank=True)

    banner_image = models.ImageField(upload_to="provider_banners/", null=True, blank=True)
    banner_image_size = models.CharField(max_length=100, null=True, blank=True)

    is_fully_verified = models.BooleanField(default=False)
    
    # Rating metadata
    average_rating = models.FloatField(default=0.0)
    total_ratings = models.IntegerField(default=0)

    # Professional Identity (Primarily for INDIVIDUAL types)
    specialization = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.verified_user.full_name or 'Unknown'} ({self.profile_status})"


class ProviderRating(models.Model):
    """
    Stores individual ratings and reviews for service providers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="ratings"
    )
    customer_id = models.UUIDField()  # Auth ID of the student/customer
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    customer_role = models.CharField(max_length=50, null=True, blank=True)
    
    service_id = models.UUIDField(null=True, blank=True)  # Optional link to a specific service
    assigned_employee_id = models.UUIDField(null=True, blank=True) # ID of staff member being rated
    
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    provider_response = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "provider_ratings"
        # Customer can rate a specific service only once (if service_id is provided)
        unique_together = ("customer_id", "provider", "service_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rating {self.rating} from {self.customer_id} for {self.provider}"


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



class ConsultationType(models.Model):
    """
    Provider-defined consultation types for veterinary/doctor bookings.
    e.g. 'General Checkup', 'Emergency', 'Follow-up', 'Specialist Consultation'.
    Pet owners choose one of these when booking a vet service.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="consultation_types"
    )
    name = models.CharField(max_length=100, help_text="e.g. 'General Checkup', 'Emergency'")
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=30, help_text="Typical consultation duration in minutes")
    consultation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Fee for this consultation type")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.provider})"


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
    version = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "name")

    def __str__(self):
        return f"{self.name} ({self.provider})"
    
    def save(self, *args, **kwargs):
        """Override save to invalidate cache for all employees with this role."""
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)
        self._invalidate_employee_caches()
    
    def delete(self, *args, **kwargs):
        """Override delete to invalidate cache before deletion."""
        self._invalidate_employee_caches()
        super().delete(*args, **kwargs)
    
    def _invalidate_employee_caches(self):
        """Invalidate permission cache for all employees assigned to this role."""
        # Import here to avoid circular import
        from .models import OrganizationEmployee
        import logging
        logger = logging.getLogger(__name__)
        
        employees = OrganizationEmployee.objects.filter(provider_role=self)
        count = employees.count()
        
        if count > 0:
            logger.info(f"🔄 Role '{self.name}' changed - invalidating cache and sync for {count} employees")
            from .kafka_producer import publish_employee_updated
            for emp in employees:
                emp.invalidate_permission_cache()
                try:
                    publish_employee_updated(emp)
                except Exception as e:
                    logger.error(f"❌ Failed to broadcast permission sync for {emp.auth_user_id}: {e}")


class ProviderRoleCapability(models.Model):
    """
    Maps ProviderRole to specific action capabilities (e.g. BOARDING_BASIC_CREATE).
    """
    provider_role = models.ForeignKey(
        ProviderRole,
        on_delete=models.CASCADE,
        related_name="capabilities"
    )
    permission_key = models.CharField(max_length=150, db_index=True)

    class Meta:
        unique_together = ("provider_role", "permission_key")

    def __str__(self):
        return f"{self.provider_role.name} - {self.permission_key}"
    
    def save(self, *args, **kwargs):
        """Override save to trigger role cache invalidation."""
        super().save(*args, **kwargs)
        self.provider_role._invalidate_employee_caches()
    
    def delete(self, *args, **kwargs):
        """Override delete to trigger role cache invalidation."""
        role = self.provider_role
        super().delete(*args, **kwargs)
        role._invalidate_employee_caches()


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
    
    # Pro Doctor Features
    specialization = models.CharField(max_length=255, blank=True, null=True, help_text="Doctor specialization (e.g. Cardiologist, Surgeon)")
    consultation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Individual doctor's consultation fee")
    
    # Rating stats
    average_rating = models.FloatField(default=0.0)
    total_ratings = models.IntegerField(default=0)
    
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
        return f"Employee {self.full_name or self.auth_user_id} of {self.organization}"

    # @deprecated - prevent new usage
    LEGACY_ROLE_MAP = {
        "receptionist": ["VETERINARY_CORE", "VETERINARY_VISITS"],
        "vitals staff": ["VETERINARY_CORE", "VETERINARY_VITALS"],
        "doctor": ["VETERINARY_CORE", "VETERINARY_VISITS", "VETERINARY_VITALS", "VETERINARY_PRESCRIPTIONS", "VETERINARY_LABS", "VETERINARY_DOCTOR"],
        "lab tech": ["VETERINARY_CORE", "VETERINARY_LABS"],
        "pharmacy": ["VETERINARY_CORE", "VETERINARY_MEDICINE_REMINDERS"],
        "employee": ["VETERINARY_CORE"]
    }

    def get_final_permissions(self):
        """
        Calculate Employee Permissions with caching.
        Rule: Effective Access = (Organization Plan Capabilities) ∩ (Employee Assigned Role)
        
        We STRICTLY enforce that an employee cannot have a permission that the Organization does not possess.
        """
        import logging
        logger = logging.getLogger(__name__)

        # Check cache first
        # 10/10 Enterprise Upgrade: Include role ID and version in cache key for instant invalidation
        role_id = self.provider_role_id or "legacy"
        role_version = self.provider_role.version if self.provider_role else 0
        cache_key = f"employee_perms_{self.id}_{role_id}_v{role_version}"
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"🔍 Cache HIT for employee {self.auth_user_id} (Role: {role_id}, Version: {role_version})")
            return cached_result

        logger.info(f"\n{'='*100}")
        logger.info(f"💾 PERMISSION CALCULATION START: Employee {self.auth_user_id}")
        logger.info(f"{'='*100}")
        logger.info(f"   Employee ID: {self.id}")
        logger.info(f"   Role String: {self.role}")
        logger.info(f"   Provider Role: {self.provider_role}")
        logger.info(f"   Organization: {self.organization.verified_user.email}")

        # 1. The Ceiling: Organization's Purchases (Upper Bound)
        org_caps = self.organization.verified_user.get_all_plan_capabilities()
        logger.info(f"\n   🏢 ORGANIZATION PLAN CAPABILITIES:")
        logger.info(f"      Count: {len(org_caps)}")
        logger.info(f"      List: {sorted(list(org_caps))}")
        
        # 2. The Selection: Employee's Assigned Role
        role_perms = set()
        
        provider_role = self.provider_role
        
        # [ENTERPRISE FALLBACK] If provider_role link is missing, attempt to resolve by role string
        if not provider_role and self.role:
            try:
                # Search for a custom role in this organization matching the string name
                from .models import ProviderRole
                provider_role = ProviderRole.objects.filter(
                    provider=self.organization,
                    name__iexact=self.role
                ).first()
                if provider_role:
                    logger.info(f"   ✨ AUTO-RESOLVED string role '{self.role}' to ProviderRole {provider_role.id}")
            except Exception as e:
                logger.error(f"   ❌ Error auto-resolving role: {e}")

        if provider_role:
            # Modern Path: Custom DB Role
            logger.info(f"\n   🎭 ROLE CAPABILITIES (Custom Role: {provider_role.name}):")
            
            # 1. Start with DB-stored capabilities
            db_caps = provider_role.capabilities.all()
            for cap in db_caps:
                role_perms.add(cap.permission_key)
            
            # 2. [FIX] If it's a System Role and DB is empty for certain keys, 
            # fall back to Template defaults (Full Access)
            if provider_role.is_system_role:
                from .role_templates import get_role_templates
                all_data = get_role_templates()
                templates = all_data.get('templates', [])
                features_meta = all_data.get('features', [])
                
                template = next((t for t in templates if t.get('name') == provider_role.name), None)
                if template:
                    feat_ids = template.get('features', [])
                    for f_id in feat_ids:
                        feat_obj = next((f for f in features_meta if f.get('id') == f_id), None)
                        if feat_obj:
                            for cap_key in feat_obj.get('capabilities', []):
                                # [AUTOMATION] Use Metadata-driven Defaults instead of hardcoded True
                                # This ensures clinical modules default to RESTRICTED for all roles
                                # unless explicitly overridden in the template.
                                defaults = feat_obj.get('default_permissions', {
                                    'can_view': True, 'can_create': True, 
                                    'can_edit': True, 'can_delete': True
                                })
                                
                                can_view = defaults.get('can_view', True)
                                can_create = defaults.get('can_create', True)
                                can_edit = defaults.get('can_edit', True)
                                can_delete = defaults.get('can_delete', True)
                                    
                                # 🛑 Apply Overrides if defined in template for THIS feature
                                if template and 'overrides' in template and f_id in template['overrides']:
                                    ovr = template['overrides'][f_id]
                                    can_view = ovr.get('can_view', can_view)
                                    can_create = ovr.get('can_create', can_create)
                                    can_edit = ovr.get('can_edit', can_edit)
                                    can_delete = ovr.get('can_delete', can_delete)

                                if can_view: role_perms.add(f"{cap_key}_VIEW")
                                if can_create: role_perms.add(f"{cap_key}_CREATE")
                                if can_edit: role_perms.add(f"{cap_key}_EDIT")
                                if can_delete: role_perms.add(f"{cap_key}_DELETE")
            
            logger.info(f"      Count: {len(role_perms)}")
            logger.info(f"      List: {sorted(list(role_perms))}")
        else:
            # Deprecated Path: Legacy Map
            legacy_key = (self.role or "employee").lower()
            legacy_keys = self.LEGACY_ROLE_MAP.get(legacy_key, [])
            for k in legacy_keys:
                role_perms.update([f"{k}_VIEW", f"{k}_CREATE", f"{k}_EDIT", f"{k}_DELETE"])
            
            logger.info(f"\n   🎭 ROLE CAPABILITIES (Legacy Role: '{legacy_key}'):")
            logger.info(f"      Count: {len(role_perms)}")
            logger.info(f"      List: {sorted(list(role_perms))}")

        # 3. The Intersection: Only allow what the Plan allows
        ALIAS_MAP = {
            "VETERINARY_SCHEDULING": "VETERINARY_SCHEDULE"
        }
        
        # Clinical keys that MUST be granular for staff
        STRICT_GRANULAR_KEYS = {
            'VETERINARY_VISITS', 'VETERINARY_PATIENTS', 'VETERINARY_VITALS', 
            'VETERINARY_PRESCRIPTIONS', 'VETERINARY_LABS', 'VETERINARY_PHARMACY',
            'VETERINARY_SCHEDULE', 'VETERINARY_ONLINE_CONSULT', 'VETERINARY_OFFLINE_VISIT',
            'VETERINARY_MEDICINE_REMINDERS', 'VETERINARY_CHECKOUT'
        }

        final_perms_list = set()
        for perm_key in role_perms:
            # Extract base key by removing _VIEW, _CREATE, _EDIT, _DELETE
            base_key = perm_key
            has_suffix = False
            for suffix in ["_VIEW", "_CREATE", "_EDIT", "_DELETE"]:
                if perm_key.endswith(suffix):
                    base_key = perm_key[:-len(suffix)]
                    has_suffix = True
                    break
            
            # [SAFE GUARD] For Staff, we strictly block the "Full Access" base keys
            # if they belong to clinical modules. They MUST have a suffix.
            if not has_suffix and base_key in STRICT_GRANULAR_KEYS:
                logger.warning(f"   ⚠️ [RBAC] Discarding unsafe base key '{perm_key}' for staff (must be granular)")
                continue

            target_key = ALIAS_MAP.get(base_key, base_key)
            if target_key in org_caps:
                # Add the flat permission key back, but using the resolved alias name if applicable
                if base_key != target_key:
                    suffix = perm_key[len(base_key):]
                    final_perms_list.add(f"{target_key}{suffix}")
                else:
                    final_perms_list.add(perm_key)
        
        logger.info(f"\n   ✂️ INTERSECTION (Plan ∩ Role):")
        logger.info(f"      Count: {len(final_perms_list)}")
        logger.info(f"      List: {sorted(list(final_perms_list))}")
        
        # 4. Core Access (Conditional)
        MANAGEMENT_KEYS = ['EMPLOYEE_MANAGEMENT', 'ROLE_MANAGEMENT', 'CUSTOMER_BOOKING', 'CLINIC_MANAGEMENT', 'SYSTEM_ADMIN']
        
        # Check if they have ANY vet capabilities or management capabilities
        has_vet_capabilities = any(cap.startswith("VETERINARY_") for cap in final_perms_list) or any(any(k in cap for k in MANAGEMENT_KEYS) for cap in final_perms_list)
        
        logger.info(f"\n   🔍 VETERINARY CHECK:")
        logger.info(f"      Has Vet Capabilities: {has_vet_capabilities}")
        
        if has_vet_capabilities:
            # Always ensure VETERINARY_CORE for medical/management staff
            if "VETERINARY_CORE_VIEW" not in final_perms_list:
                final_perms_list.update(["VETERINARY_CORE_VIEW", "VETERINARY_CORE_CREATE", "VETERINARY_CORE_EDIT"])
                logger.info(f"      ✅ Added VETERINARY_CORE basics")
            
            # Map CLINIC_MANAGEMENT to the medical-specific ADMIN_SETTINGS capability if missing
            if any("CLINIC_MANAGEMENT" in p for p in final_perms_list) and not any("VETERINARY_ADMIN_SETTINGS" in p for p in final_perms_list):
                final_perms_list.update([
                    "VETERINARY_ADMIN_SETTINGS_VIEW", "VETERINARY_ADMIN_SETTINGS_CREATE",
                    "VETERINARY_ADMIN_SETTINGS_EDIT", "VETERINARY_ADMIN_SETTINGS_DELETE"
                ])
                logger.info(f"      ✅ Synced CLINIC_MANAGEMENT -> VETERINARY_ADMIN_SETTINGS")

        # 5. Apply Overrides (permissions_json)
        overrides = self.permissions_json or {}
        add_overrides = overrides.get("ADD", [])
        remove_overrides = overrides.get("REMOVE", [])

        logger.info(f"\n   🎚️ OVERRIDES:")
        logger.info(f"      ADD: {sorted(list(add_overrides))}")
        logger.info(f"      REMOVE: {sorted(list(remove_overrides))}")

        for cap_key in add_overrides:
            # User might pass base keys in overrides, convert to full suite if so
            if not any(cap_key.endswith(sfx) for sfx in ["_VIEW", "_CREATE", "_EDIT", "_DELETE"]):
                final_perms_list.update([f"{cap_key}_VIEW", f"{cap_key}_CREATE", f"{cap_key}_EDIT", f"{cap_key}_DELETE"])
            else:
                final_perms_list.add(cap_key)
        
        for cap_key in remove_overrides:
            if not any(cap_key.endswith(sfx) for sfx in ["_VIEW", "_CREATE", "_EDIT", "_DELETE"]):
                # Remove all variants
                final_perms_list = {p for p in final_perms_list if not p.startswith(cap_key)}
            else:
                final_perms_list.discard(cap_key)

        logger.info(f"\n   🎯 FINAL RESULT:")
        logger.info(f"      Count: {len(final_perms_list)}")
        logger.info(f"      List: {sorted(list(final_perms_list))}")
        logger.info(f"{'='*100}\n")
        
        # Convert final set to a list for JSON compatibility
        final_perms_list = list(final_perms_list)
        
        # Cache for 1 hour
        cache.set(cache_key, final_perms_list, 3600)
        return final_perms_list
    
    def save(self, *args, **kwargs):
        """Override save to invalidate cache when role changes."""
        # Force standardized system role to "employee"
        self.role = "employee"

        # Check if provider_role changed
        if self.pk:
            try:
                old_instance = OrganizationEmployee.objects.get(pk=self.pk)
                if old_instance.provider_role != self.provider_role:
                    import logging
                    logging.getLogger(__name__).info(
                        f"🔄 Employee {self.auth_user_id} provider_role changed: "
                        f"{old_instance.provider_role} → {self.provider_role}"
                    )
            except OrganizationEmployee.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Always invalidate cache after save
        self.invalidate_permission_cache()

    def invalidate_permission_cache(self):
        """
        Force clear the permission cache for this employee.
        Since we use a versioned key, we should ideally clear all potential variations
        or use a pattern if the cache backend supports it. For now, we clear the current one.
        """
        from django.core.cache import cache
        import logging
        logger = logging.getLogger(__name__)

        role_id = self.provider_role_id or "legacy"
        role_version = self.provider_role.version if self.provider_role else 0
        cache_key = f"employee_perms_{self.id}_{role_id}_v{role_version}"
        cache.delete(cache_key)
        
        # Also clear the generic one if it exists from previous versions
        cache.delete(f"employee_perms_{self.id}_v{role_version}")
        
        logger.info(f"♻️  Invalidated permission cache for employee {self.id} (Key: {cache_key})")


class EmployeeServiceMapping(models.Model):
    """
    Mapping between employees and the services (facilities) they are qualified to perform.
    Enables Model 2: Service-First Smart Assignment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        OrganizationEmployee, 
        on_delete=models.CASCADE, 
        related_name="service_mappings"
    )
    facility = models.ForeignKey(
        'provider_dynamic_fields.ProviderTemplateFacility', 
        on_delete=models.CASCADE, 
        related_name="employee_mappings"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'facility')
        verbose_name = "Employee Service Mapping"
        verbose_name_plural = "Employee Service Mappings"

    def __str__(self):
        return f"{self.employee.full_name} -> {self.facility.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate the employee's permission cache when mappings change
        self.employee.invalidate_permission_cache()


class EmployeeAvailability(models.Model):
    """Weekly working hours for organization employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        "service_provider.OrganizationEmployee",
        on_delete=models.CASCADE,
        related_name="availability"
    )
    day_of_week = models.IntegerField(help_text="0-6 (Mon-Sun)")
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("employee", "day_of_week")
        ordering = ["day_of_week", "start_time"]


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


class DashboardWidget(models.Model):
    """
    Registry of available dashboard components.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True) # e.g. 'doctor-queue'
    label = models.CharField(max_length=255)
    component_name = models.CharField(max_length=255) # e.g. 'DoctorQueueWidget'
    
    # 10/10 Enterprise Requirement: ManyToMany capabilities + Logic
    required_capabilities = models.ManyToManyField(Capability, related_name="widgets")
    logic_type = models.CharField(
        max_length=10, 
        choices=[('AND', 'AND'), ('OR', 'OR')], 
        default='OR'
    )
    
    default_config = models.JSONField(default=dict, blank=True) # w, h, x, y
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label} ({self.key})"


class UserDashboardLayout(models.Model):
    """
    Personalized dashboard layout for a user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(VerifiedUser, on_delete=models.CASCADE, related_name="dashboard_layout")
    layout_json = models.JSONField(default=list) # [{widget_key, x, y, w, h}]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Layout for {self.user.email}"


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

class AuditLog(models.Model):
    """
    Logs critical system changes for auditability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=100) # e.g. 'ROLE_UPDATED', 'PERMISSIONS_SYNCED'
    actor_id = models.UUIDField(null=True, blank=True) # Auth ID of the person performing change
    target_id = models.UUIDField() # ID of the object changed
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

# Signal to log role changes
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=ProviderRole)
def log_role_change(sender, instance, created, **kwargs):
    AuditLog.objects.create(
        action='ROLE_CREATED' if created else 'ROLE_UPDATED',
        target_id=instance.id,
        details={
            'name': instance.name,
            'version': instance.version,
            'capabilities': list(instance.capabilities.values_list('permission_key', flat=True))
        }
    )


class BillingProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    verified_user = models.OneToOneField(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="billing_profile"
    )
    company_name = models.CharField(max_length=255, blank=True, null=True)
    billing_email = models.EmailField(blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    vat_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Billing -> {self.company_name or self.verified_user.email}"


class PermissionAuditLog(models.Model):
    """
    Audit log for tracking permission and role changes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        VerifiedUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="audit_actions"
    )
    target_employee = models.ForeignKey(
        OrganizationEmployee, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="audit_logs"
    )
    target_role = models.ForeignKey(
        ProviderRole, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="audit_logs"
    )
    action = models.CharField(max_length=50) # e.g. ROLE_ASSIGNED, CAPABILITY_ADDED, etc.
    details = models.JSONField(default=dict) # Store old/new values
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "permission_audit_logs"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} by {self.actor} on {self.timestamp}"

    @classmethod
    def log_action(cls, actor, action, target_employee=None, target_role=None, details=None, request=None):
        """
        Helper to create an audit log entry.
        """
        ip = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')

        # 🛡️ Guard: Actor MUST be a VerifiedUser instance for the ForeignKey
        # If it's a TransientUser (Pet Owner / external Super Admin), set actor=None and log in details
        actual_actor = actor if (actor and hasattr(actor, '_state')) else None
        
        final_details = details or {}
        if not actual_actor and actor:
            final_details['actor_info'] = str(actor)
            if hasattr(actor, 'email'): final_details['actor_email'] = actor.email

        return cls.objects.create(
            actor=actual_actor,
            target_employee=target_employee,
            target_role=target_role,
            action=action,
            details=final_details,
            ip_address=ip
        )


class ProviderProfile(models.Model):
    """
    Detailed profile information for a provider.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="detailed_profile"
    )
    about_text = models.TextField(blank=True, null=True)
    years_of_experience = models.IntegerField(default=0)
    specializations = models.TextField(blank=True, null=True)
    clinic_name = models.CharField(max_length=255, blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True, null=True)
    
    profile_image = models.ImageField(upload_to="provider_profiles/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="provider_covers/", null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.provider}"


class ProviderService(models.Model):
    """
    Provider-specific configuration for a service.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="custom_services"
    )
    template_service_id = models.UUIDField()
    custom_description = models.TextField(blank=True, null=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "template_service_id")

    def __str__(self):
        return f"{self.provider} - Service {self.template_service_id}"


class ProviderServiceImage(models.Model):
    """
    Images for a specific provider service.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_service = models.ForeignKey(
        ProviderService,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="service_images/")
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class ProviderCertification(models.Model):
    """
    Professional certifications and documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="certifications"
    )
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to="provider_certs/")
    issued_by = models.CharField(max_length=255, blank=True, null=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    verified_by_admin = models.BooleanField(default=False)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.provider}"


class ProviderGallery(models.Model):
    """
    General professional gallery.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="gallery"
    )
    image = models.ImageField(upload_to="provider_gallery/")
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class ProviderPolicy(models.Model):
    """
    Business policies.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="policy"
    )
    cancellation_policy = models.TextField(blank=True, null=True)
    reschedule_policy = models.TextField(blank=True, null=True)
    safety_measures = models.TextField(blank=True, null=True)
    house_rules = models.TextField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Policies for {self.provider}"

# ── SIGNALS ──
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=ProviderPermission)
def invalidate_staff_cache_on_permission_change(sender, instance, **kwargs):
    """
    Automatically invalidates permission cache for all staff when the
    provider's granular permission mappings (VIEW/CREATE/EDIT/DELETE) change.
    """
    try:
        v_user = instance.verified_user
        employees = OrganizationEmployee.objects.filter(organization__verified_user=v_user)
        for emp in employees:
            emp.invalidate_permission_cache()
            # Push Kafka update if needed
            from .kafka_producer import publish_employee_updated
            publish_employee_updated(emp)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"❌ Error syncing staff perms on Permission change: {e}")

@receiver([post_save, post_delete], sender='provider_dynamic_fields.ProviderCapabilityAccess')
def invalidate_staff_cache_on_capability_change(sender, instance, **kwargs):
    """
    Automatically invalidates permission cache for all staff when the
    Plan-level capability access is modified.
    """
    try:
        from .models import VerifiedUser
        v_user = VerifiedUser.objects.filter(auth_user_id=instance.provider_id).first()
        if v_user:
            employees = OrganizationEmployee.objects.filter(organization__verified_user=v_user)
            for emp in employees:
                emp.invalidate_permission_cache()
                from .kafka_producer import publish_employee_updated
                publish_employee_updated(emp)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"❌ Error syncing staff perms on Capability change: {e}")
