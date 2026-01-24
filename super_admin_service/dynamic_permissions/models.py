import uuid
from django.db import models
from django.conf import settings
from admin_core.models import VerifiedUser

class Capability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True, help_text="Technical key e.g. VETERINARY_DOCTOR")
    name = models.CharField(max_length=255, help_text="Human readable name")
    description = models.TextField(blank=True, null=True)
    service_type = models.CharField(max_length=100, default="VETERINARY", help_text="Service grouping")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.key})"

class FeatureModule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True, help_text="Unique key for the module")
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE, related_name="modules")
    
    name = models.CharField(max_length=255)
    route = models.CharField(max_length=255, help_text="Frontend route path or name")
    api_pattern = models.CharField(max_length=255, blank=True, null=True, help_text="Regex for API matching if needed")
    
    icon = models.CharField(max_length=100, default="tabler-box")
    sequence = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.key})"

class PlanCapability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # We reference Plan by string to avoid circular imports if strictly needed, 
    # but since plans_coupens is established, we can use string reference.
    plan = models.ForeignKey('plans_coupens.Plan', on_delete=models.CASCADE, related_name="linked_permission_capabilities")
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE, related_name="plans")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('plan', 'capability')

    def __str__(self):
        return f"{self.plan} -> {self.capability}"

class ProviderCapability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # We link to VerifiedUser using auth_user_id
    user = models.ForeignKey(
        VerifiedUser, 
        on_delete=models.CASCADE, 
        related_name="dynamic_capabilities",
        to_field='auth_user_id',
        db_column='user_auth_id'
    )
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE)
    
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'capability')
        
    def __str__(self):
        return f"{self.user} -> {self.capability}"
