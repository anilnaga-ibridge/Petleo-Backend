from rest_framework import serializers
from .models import Facility

class FacilitySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="category.name", read_only=True
    )
    service_display = serializers.CharField(
        source="category.service.display_name", read_only=True
    )

    class Meta:
        model = Facility
        fields = [
            "id",
            "category",
            "category_display",
            "service_display",
            "name",
            "value",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

