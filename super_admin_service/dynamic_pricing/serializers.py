from rest_framework import serializers
from .models import Pricing

class PricingSerializer(serializers.ModelSerializer):
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
        model = Pricing
        fields = "__all__"  # This will NOT include display fields, so add below
        extra_fields = ["service_display", "category_display", "facility_display"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["service_display"] = instance.service.display_name if instance.service else None
        data["category_display"] = instance.category.name if instance.category else None
        data["facility_display"] = instance.facility.name if instance.facility else None
        return data
