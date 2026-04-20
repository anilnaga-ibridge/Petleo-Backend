from django.contrib import admin
from .models import (
    Plan, PlanCapability, PurchasedPlan, ProviderPlanCapability,
    TaxConfiguration, BillingSequence, Invoice, BillingAuditLog
)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("title", "target_type", "billing_cycle", "price", "is_active")
    search_fields = ("title", "slug")

@admin.register(PlanCapability)
class PlanCapabilityAdmin(admin.ModelAdmin):
    list_display = ("plan", "service", "category", "facility")

@admin.register(PurchasedPlan)
class PurchasedPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "billing_cycle", "start_date", "is_active", "status")
    list_filter = ("status", "is_active")

@admin.register(ProviderPlanCapability)
class ProviderPlanCapabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "service", "category", "facility")

@admin.register(TaxConfiguration)
class TaxConfigurationAdmin(admin.ModelAdmin):
    list_display = ("key", "rate", "is_active")

@admin.register(BillingSequence)
class BillingSequenceAdmin(admin.ModelAdmin):
    list_display = ("year", "last_number")

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "provider", "total_amount", "status", "issued_at")
    list_filter = ("status", "tax_mode")
    search_fields = ("invoice_number", "provider__email")

@admin.register(BillingAuditLog)
class BillingAuditLogAdmin(admin.ModelAdmin):
    list_display = ("invoice", "event_type", "created_at")

