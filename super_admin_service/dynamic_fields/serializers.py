# from rest_framework import serializers
# from .models import ProviderFieldDefinition, ProviderFieldValue


# class ProviderFieldDefinitionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProviderFieldDefinition
#         fields = "__all__"


# class ProviderFieldValueSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProviderFieldValue
#         fields = "__all__"
from rest_framework import serializers
from .models import ProviderFieldDefinition

class ProviderFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderFieldDefinition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
