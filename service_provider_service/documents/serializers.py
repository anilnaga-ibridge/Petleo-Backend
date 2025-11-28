from rest_framework import serializers
from .models import Provider, ProviderDocumentSubmission

class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "name", "email", "role", "created_at"]

class ProviderDocumentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderDocumentSubmission
        fields = "__all__"
        read_only_fields = ("status", "submitted_at", "verified_at")
