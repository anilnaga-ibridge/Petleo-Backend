
from django.contrib import admin
from .models import Plan, PlanPrice, PlanCapability, BillingCycle, PurchasedPlan, ProviderPlanCapability

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("title", "role", "is_active", "default_billing_cycle")
    search_fields = ("title", "slug")

@admin.register(PlanPrice)
class PlanPriceAdmin(admin.ModelAdmin):
    list_display = ("plan", "billing_cycle", "amount", "currency", "is_active")

@admin.register(PlanCapability)
class PlanCapabilityAdmin(admin.ModelAdmin):
    list_display = ("plan", "service", "category", "facility", "can_create", "can_view", "can_edit", "can_delete")

@admin.register(BillingCycle)
class BillingCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_value", "duration_type", "is_active")

@admin.register(PurchasedPlan)
class PurchasedPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "billing_cycle", "start_date", "is_active")

@admin.register(ProviderPlanCapability)
class ProviderPlanCapabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "service", "category", "facility", "can_view", "can_create", "can_edit", "can_delete")
