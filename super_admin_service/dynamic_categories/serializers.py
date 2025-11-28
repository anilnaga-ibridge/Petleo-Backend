from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    service_display = serializers.CharField(source='service.display_name', read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "service",
            "service_display",   # 👈 Required for frontend table
            "name",
            "value",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
