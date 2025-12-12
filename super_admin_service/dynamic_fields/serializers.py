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


from .models import ProviderDocumentVerification
from admin_core.models import VerifiedUser

class ProviderDocumentVerificationSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()
    provider_role = serializers.SerializerMethodField()

    class Meta:
        model = ProviderDocumentVerification
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "auth_user_id", "document_id", "file_url", "filename")

    def get_provider_name(self, obj):
        try:
            # Try fetching from local DB first (fastest)
            user = VerifiedUser.objects.get(auth_user_id=obj.auth_user_id)
            return user.full_name
        except VerifiedUser.DoesNotExist:
            # Fallback to API call
            try:
                import requests
                response = requests.get(f"http://127.0.0.1:8002/api/provider/profile/{obj.auth_user_id}/")
                if response.status_code == 200:
                    return response.json().get("full_name", "Unknown Provider")
            except Exception:
                pass
            return "Unknown Provider"

    def get_provider_role(self, obj):
        try:
            # Try fetching from local DB first
            user = VerifiedUser.objects.get(auth_user_id=obj.auth_user_id)
            return user.role
        except VerifiedUser.DoesNotExist:
            # Fallback to API call
            try:
                import requests
                response = requests.get(f"http://127.0.0.1:8000/auth/roles/public/{obj.auth_user_id}")
                if response.status_code == 200:
                    return response.json().get("role", "Unknown Role")
            except Exception:
                pass
            return "Unknown Role"
