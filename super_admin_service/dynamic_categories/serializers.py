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
            "category_key",
            "is_active",
            "is_system",
            "created_at",
            "updated_at",
        ]

    def _handle_capability_creation(self, validated_data):
        cat_key = validated_data.get('category_key')
        if cat_key:
            from dynamic_permissions.models import Capability
            # Check if it exists, if not create it
            if not Capability.objects.filter(key=cat_key).exists():
                Capability.objects.create(
                    key=cat_key,
                    name=validated_data.get('name', linked_cap), # Fallback to Category Name
                    description=f"Auto-generated for Feature: {validated_data.get('name')}",
                    service_type="GENERATED"
                )

    def create(self, validated_data):
        self._handle_capability_creation(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._handle_capability_creation(validated_data)
        return super().update(instance, validated_data)
