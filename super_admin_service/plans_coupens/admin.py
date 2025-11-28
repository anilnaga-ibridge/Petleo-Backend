from django.contrib import admin

# Register your models here.

# # Register your models here.
# # plans_coupens/admin.py
# from django.contrib import admin
# from .models import Plan, PlanPrice, PlanItem, BillingCycle, PurchasedPlan, ProviderPlanPermission

# @admin.register(Plan)
# class PlanAdmin(admin.ModelAdmin):
#     list_display = ("title", "role", "is_active", "default_billing_cycle")
#     search_fields = ("title", "slug")

# @admin.register(PlanPrice)
# class PlanPriceAdmin(admin.ModelAdmin):
#     list_display = ("plan", "billing_cycle", "amount", "currency", "is_active")

# @admin.register(PlanItem)
# class PlanItemAdmin(admin.ModelAdmin):
#     list_display = ("plan", "service", "category", "can_create", "can_view", "can_edit", "can_delete")

# @admin.register(BillingCycle)
# class BillingCycleAdmin(admin.ModelAdmin):
#     list_display = ("name", "duration_value", "duration_type", "is_active")

# @admin.register(PurchasedPlan)
# class PurchasedPlanAdmin(admin.ModelAdmin):
#     list_display = ("user", "plan", "billing_cycle", "start_date", "is_active")

# @admin.register(ProviderPlanPermission)
# class ProviderPlanPermissionAdmin(admin.ModelAdmin):
#     list_display = ("user", "plan", "service", "category", "can_view", "can_create", "can_edit", "can_delete")
