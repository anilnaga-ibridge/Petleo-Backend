from django.db import models

# Create your models here.
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from service_provider.models import VerifiedUser


class ProviderCart(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("checked_out", "Checked Out"),
        ("abandoned", "Abandoned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="carts"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} - {self.verified_user.full_name}"

    @property
    def total_amount(self) -> Decimal:
        return sum((item.price_amount for item in self.items.all()), Decimal("0.00"))


class ProviderCartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    cart = models.ForeignKey(
        ProviderCart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # ✅ Copied from SuperAdmin Plan API
    plan_id = models.UUIDField()
    plan_title = models.CharField(max_length=255)
    plan_role = models.CharField(max_length=20)

    billing_cycle_id = models.IntegerField()
    billing_cycle_name = models.CharField(max_length=100)

    price_amount = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10, default="INR")

    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("cart", "plan_id", "billing_cycle_id")

    def __str__(self):
        return f"{self.plan_title} ({self.billing_cycle_name})"


class PurchasedPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to local VerifiedUser
    verified_user = models.ForeignKey(
        VerifiedUser,
        on_delete=models.CASCADE,
        related_name="purchased_plans"
    )

    # Plan Details (Snapshot)
    plan_id = models.UUIDField()
    plan_title = models.CharField(max_length=255)
    
    billing_cycle_id = models.IntegerField()
    billing_cycle_name = models.CharField(max_length=100)
    
    price_amount = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=10, default="INR")
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.plan_title} - {self.verified_user.full_name}"
