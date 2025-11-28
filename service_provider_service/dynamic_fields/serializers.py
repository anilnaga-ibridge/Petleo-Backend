# serializers.py
from rest_framework import serializers
from .models import LocalFieldDefinition, ProviderFieldValue


class LocalFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalFieldDefinition
        fields = "__all__"


class ProviderFieldValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderFieldValue
        fields = "__all__"
        read_only_fields = ("id", "updated_at")


class ProviderSubmitFieldSerializer(serializers.Serializer):
    field_id = serializers.UUIDField()
    value = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)

    def validate(self, data):
        field_id = data["field_id"]

        try:
            field_def = LocalFieldDefinition.objects.get(id=field_id)
        except LocalFieldDefinition.DoesNotExist:
            raise serializers.ValidationError("Invalid field_id")

        if field_def.is_required and (data.get("value") in (None, "", [], {})):
            raise serializers.ValidationError(f"{field_def.label} is required")

        return data
