from rest_framework import serializers
from .models import DocumentDefinition

class DocumentDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentDefinition
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")
