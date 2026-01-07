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
    is_active = models.BooleanField(default=True)
    blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

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
