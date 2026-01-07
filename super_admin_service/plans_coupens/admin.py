from django.contrib import admin
from .models import Plan, PlanCapability, PurchasedPlan, ProviderPlanCapability

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("title", "target_type", "billing_cycle", "price", "is_active")
    search_fields = ("title", "slug")

@admin.register(PlanCapability)
class PlanCapabilityAdmin(admin.ModelAdmin):
    list_display = ("plan", "service", "category", "facility")

@admin.register(PurchasedPlan)
class PurchasedPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "billing_cycle", "start_date", "is_active")

@admin.register(ProviderPlanCapability)
class ProviderPlanCapabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "service", "category", "facility")
