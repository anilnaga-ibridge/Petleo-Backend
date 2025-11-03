# from django.db import models
# from django.utils import timezone
# import uuid
# class BillingCycle(models.Model):
#     """
#     Represents a billing cycle such as Daily, Weekly, Monthly, Yearly, or custom.
#     """
#     DURATION_TYPE_CHOICES = [
#         ("days", "Days"),
#         ("weeks", "Weeks"),
#         ("months", "Months"),
#         ("years", "Years"),
#     ]

#     id = models.AutoField(primary_key=True)
#     name = models.CharField(max_length=50, unique=True)
#     duration_value = models.PositiveIntegerField(default=1)  # e.g. 7
#     duration_type = models.CharField(max_length=10, choices=DURATION_TYPE_CHOICES, default="months")  # e.g. days/weeks/months
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     def __str__(self):
#         return f"{self.name} ({self.duration_value} {self.duration_type})"

# class Plan(models.Model):
#     """
#     Subscription Plan definition
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     title = models.CharField(max_length=255)
#     slug = models.SlugField(unique=True)
#     role_name = models.CharField(max_length=100)
#     role = models.CharField(max_length=100, default="individual")
#     subtitle = models.CharField(max_length=255, blank=True)
#     description = models.TextField(blank=True, null=True)
#     features = models.JSONField(default=dict, blank=True, null=True)
#     is_active = models.BooleanField(default=True)
#     default_billing_cycle = models.ForeignKey(
#         "BillingCycle", on_delete=models.SET_NULL, null=True, blank=True
#     )
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.title


# class PlanPrice(models.Model):
#     """
#     Price for each billing cycle under a plan
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
#     billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     currency = models.CharField(max_length=10, default="USD")
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.plan.title} - {self.billing_cycle.name} ({self.amount} {self.currency})"


# class PlanItem(models.Model):
#     """
#     Permissions for each child service in a plan
#     """
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="items")
#     child_service_key = models.CharField(max_length=100)
#     can_view = models.BooleanField(default=False)
#     can_create = models.BooleanField(default=False)
#     can_edit = models.BooleanField(default=False)
#     can_delete = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{self.plan.title} - {self.child_service_key}"


# class Coupon(models.Model):
#     """
#     Coupon / Discount management
#     """
#     DISCOUNT_TYPE_CHOICES = [
#         ("percent", "Percent"),
#         ("fixed", "Fixed Amount"),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     code = models.CharField(max_length=50, unique=True)
#     discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
#     discount_value = models.DecimalField(max_digits=6, decimal_places=2)
#     max_uses = models.PositiveIntegerField(default=1)
#     used_count = models.PositiveIntegerField(default=0)
#     start_date = models.DateTimeField(default=timezone.now)
#     end_date = models.DateTimeField(null=True, blank=True)
#     applicable_roles = models.JSONField(default=list, blank=True, null=True)
#     applies_to_plans = models.ManyToManyField(Plan, blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     def is_valid(self, now=None):
#         now = now or timezone.now()
#         if not self.is_active:
#             return False
#         if self.end_date and self.end_date < now:
#             return False
#         if self.used_count >= self.max_uses:
#             return False
#         return True

#     def __str__(self):
#         return f"{self.code} ({self.discount_type})"
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import uuid

from dynamic_services.models import Service
from dynamic_categories.models import Category


# ------------------ BILLING CYCLE ------------------
class BillingCycle(models.Model):
    """
    Defines a billing frequency (Daily, Weekly, Monthly, Yearly, etc.)
    """
    DURATION_TYPE_CHOICES = [
        ("days", "Days"),
        ("weeks", "Weeks"),
        ("months", "Months"),
        ("years", "Years"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    duration_value = models.PositiveIntegerField(default=1)
    duration_type = models.CharField(
        max_length=10, choices=DURATION_TYPE_CHOICES, default="months"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.duration_value} {self.duration_type})"


# ------------------ PLAN ------------------
class Plan(models.Model):
    """
    Subscription Plan (e.g., 'Pro Groomer', 'Basic Daycare')
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    role_name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, default="individual")
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    features = models.JSONField(default=dict, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    default_billing_cycle = models.ForeignKey(
        "BillingCycle", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ------------------ PLAN PRICE ------------------
class PlanPrice(models.Model):
    """
    Pricing for each billing cycle under a Plan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
    billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.plan.title} - {self.billing_cycle.name} ({self.amount} {self.currency})"


# ------------------ PLAN ITEM ------------------
class PlanItem(models.Model):
    """
    Defines service & category-level permissions within a plan.
    Example:
        Plan: Groomer Pro
        Service: Grooming
        Category: Bathing, Nail Cutting
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey("Plan", on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="plan_items", null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="plan_items", null=True, blank=True)
    child_service_key = models.CharField(max_length=100, null=True, blank=True)

    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ("plan", "service", "category")

    def __str__(self):
        if self.service and self.category:
            return f"{self.plan.title} - {self.service.display_name} > {self.category.name}"
        else:
            return f"{self.plan.title} - {self.child_service_key or 'Unknown'}"


# ------------------ COUPON ------------------
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

    def __str__(self):
        return f"{self.code} ({self.discount_type})"
