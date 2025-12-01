from rest_framework import serializers
from .models import ProviderFieldDefinition, ProviderDocumentDefinition


class ProviderFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderFieldDefinition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ProviderDocumentDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderDocumentDefinition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
