



import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

from dynamic_services.models import Service
from dynamic_categories.models import Category
from dynamic_facilities.models import Facility


class BillingCycle(models.Model):
    DURATION_TYPE_CHOICES = [
        ("days", "Days"),
        ("weeks", "Weeks"),
        ("months", "Months"),
        ("years", "Years"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    duration_value = models.PositiveIntegerField(default=1)
    duration_type = models.CharField(max_length=10, choices=DURATION_TYPE_CHOICES, default="months")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.duration_value} {self.duration_type})"


class Plan(models.Model):
    ROLE_CHOICES = [
        ("individual", "Individual"),
        ("organization", "Organization"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    features = models.JSONField(default=list, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    default_billing_cycle = models.ForeignKey(
        BillingCycle, on_delete=models.SET_NULL, null=True, blank=True, related_name="default_plans"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Plan.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.role})"


class PlanPrice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
    billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("plan", "billing_cycle")

    def __str__(self):
        return f"{self.plan.title} - {self.billing_cycle.name} ({self.amount} {self.currency})"


class PlanItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="items")

    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)

    facilities = models.ManyToManyField(Facility, blank=True, related_name="plan_items")

    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ("plan", "service", "category")

    def __str__(self):
        svc = self.service.display_name if self.service else "NoService"
        cat = self.category.name if self.category else "NoCategory"
        return f"{self.plan.title} - {svc} > {cat}"

    
class Coupon(models.Model):
    """
    Coupon / Discount management for Plans.
    """
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percent"),
        ("fixed", "Fixed Amount"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=6, decimal_places=2)

    max_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    applicable_roles = models.JSONField(default=list, blank=True, null=True)
    applies_to_plans = models.ManyToManyField(Plan, blank=True)

    min_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self, now=None):
        now = now or timezone.now()
        if not self.is_active:
            return False
        if self.end_date and self.end_date < now:
            return False
        if self.used_count >= self.max_uses:
            return False
        return True

    def clean(self):
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValidationError("Percent discount cannot exceed 100%.")

    def __str__(self):
        return f"{self.code} ({self.discount_type})"


class PurchasedPlan(models.Model):
    """
    When a user buys a plan this records the purchase and billing cycle.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchased_plans")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="purchases")
    billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.SET_NULL, null=True, blank=True)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "plan", "billing_cycle")

    def __str__(self):
        return f"{self.user} purchased {self.plan.title}"


class ProviderPlanPermission(models.Model):
    """
    Actual permissions assigned to a user (provider) after purchasing a plan.
    Copied from PlanItem templates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_permissions")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="assigned_permissions")

    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)

    facilities = models.ManyToManyField(Facility, blank=True, related_name="provider_permissions")

    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "plan", "service", "category")

    def __str__(self):
        return f"{self.user} - {self.plan.title} ({self.service} / {self.category})"