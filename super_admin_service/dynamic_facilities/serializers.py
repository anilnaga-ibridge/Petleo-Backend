from rest_framework import serializers
from .models import Facility

class FacilitySerializer(serializers.ModelSerializer):
    service_display = serializers.CharField(
        source="service.display_name", read_only=True
    )

    class Meta:
        model = Facility
        fields = [
            "id",
            "service",
            "service_display",   # 👈 Add this (UI uses this)
            "name",
            "value",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

