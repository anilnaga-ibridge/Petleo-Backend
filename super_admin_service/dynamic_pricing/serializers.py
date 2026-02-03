from rest_framework import serializers
from .models import PricingRule
from dynamic_categories.serializers import CategorySerializer
from dynamic_facilities.serializers import FacilitySerializer

class PricingRuleSerializer(serializers.ModelSerializer):
    service_display = serializers.CharField(
        source="service.display_name", read_only=True
    )
    category_display = serializers.CharField(
        source="category.name", read_only=True
    )
    facility_display = serializers.CharField(
        source="facility.name", read_only=True
    )

    class Meta:
        model = PricingRule
        fields = "__all__"  # This will NOT include display fields, so add below
        extra_fields = ["service_display", "category_display", "facility_display"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add display fields for backwards compatibility or simple lookups
        data["service_display"] = instance.service.display_name if instance.service else None
        data["category_display"] = instance.category.name if instance.category else None
        data["facility_display"] = instance.facility.name if instance.facility else None
        
        # Add nested objects for frontend hierarchy grouping
        if instance.category:
            data["category"] = CategorySerializer(instance.category).data
        if instance.facility:
            data["facility"] = FacilitySerializer(instance.facility).data
            
        return data
