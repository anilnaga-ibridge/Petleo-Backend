import uuid
from django.db import models

class BillingUnit(models.TextChoices):
    HOURLY = "HOURLY", "Hourly"
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"
    PER_SESSION = "PER_SESSION", "Per Session"
    ONE_TIME = "ONE_TIME", "One Time"

class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    default_billing_unit = models.CharField(
        max_length=20,
        choices=BillingUnit.choices,
        default=BillingUnit.PER_SESSION
    )
    class TargetAudience(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        ORGANIZATION = "ORGANIZATION", "Organization"
        BOTH = "BOTH", "Both"

    target_audience = models.CharField(
        max_length=20,
        choices=TargetAudience.choices,
        default=TargetAudience.BOTH
    )
    is_active = models.BooleanField(default=True)
    blocked = models.BooleanField(default=False)
    linked_capability = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        unique=True,  # Prevent duplicate capability keys
        help_text="Technical capability key for dynamic permissions (e.g. GROOMING, DAYCARE)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        """
        Auto-generate linked_capability from display_name if not provided.
        This ensures non-technical admins don't need to manually set it.
        Handles duplicates by appending a number (e.g., PET_SPA_2).
        """
        if not self.linked_capability:
            import re
            # Convert display_name to UPPER_SNAKE_CASE
            # "Pet Spa" -> "PET_SPA"
            # "Pet Walking & Sitting" -> "PET_WALKING_SITTING"
            clean_name = re.sub(r'[^\w\s]', '', self.display_name)
            clean_name = re.sub(r'\s+', '_', clean_name.strip())
            base_capability = clean_name.upper()
            
            # Check for duplicates and append number if needed
            capability = base_capability
            counter = 2
            while Service.objects.filter(linked_capability=capability).exclude(pk=self.pk).exists():
                capability = f"{base_capability}_{counter}"
                counter += 1
            
            self.linked_capability = capability
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.name
class Capability(models.Model):
    """
    Human-readable labels and descriptions for technical capability keys.
    """
    key = models.CharField(max_length=100, primary_key=True)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    group = models.CharField(max_length=100, default="General")
    service = models.CharField(max_length=50, default="VETERINARY")

    def __str__(self):
        return f"[{self.service}] [{self.group}] {self.label}"
