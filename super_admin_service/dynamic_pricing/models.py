import uuid
from django.db import models
from dynamic_services.models import Service, BillingUnit
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility

class PricingRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="pricing_rules")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    
    billing_unit = models.CharField(
        max_length=20,
        choices=BillingUnit.choices,
        default=BillingUnit.PER_SESSION
    )
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duration in minutes for PER_SESSION or HOURLY")
    currency_code = models.CharField(max_length=3, default="INR")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service.display_name} - {self.base_price} ({self.billing_unit})"
