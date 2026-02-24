from django.db import models
import uuid
from dynamic_services.models import Service
from dynamic_categories.models import Category
from django.utils.text import slugify

class Facility(models.Model):
    PROTOCOL_CHOICES = [
        ('MINUTES_BASED', 'Minutes Based (Slots)'),
        ('SESSION_BASED', 'Session Based (Packages)'),
        ('DAY_BASED', 'Day Based (Date Range)'),
    ]
    
    STRATEGY_CHOICES = [
        ('FIXED', 'Fixed Total Price'),
        ('PER_UNIT', 'Per Unit (Min/Hr/Day)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="facilities")
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    
    # New Protocol & Pricing Fields
    protocol_type = models.CharField(max_length=20, choices=PROTOCOL_CHOICES, default='MINUTES_BASED')
    duration_minutes = models.IntegerField(default=60, help_text="Duration for slots/sessions in minutes")
    pricing_strategy = models.CharField(max_length=20, choices=STRATEGY_CHOICES, default='FIXED')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.value:
            self.value = slugify(self.name).replace("-", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.category.name})"
