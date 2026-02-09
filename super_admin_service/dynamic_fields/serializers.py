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
    provider_email = serializers.SerializerMethodField()
    provider_phone = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()

    class Meta:
        model = ProviderDocumentVerification
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "auth_user_id", "document_id", "file_url", "filename")

    def get_provider_name(self, obj):
        try:
            user = VerifiedUser.objects.get(auth_user_id=obj.auth_user_id)
            return user.full_name
        except VerifiedUser.DoesNotExist:
            return "Unknown Provider"

    def get_provider_email(self, obj):
        try:
            user = VerifiedUser.objects.get(auth_user_id=obj.auth_user_id)
            return user.email
        except VerifiedUser.DoesNotExist:
            return "N/A"

    def get_provider_phone(self, obj):
        try:
            user = VerifiedUser.objects.get(auth_user_id=obj.auth_user_id)
            return user.phone_number
        except VerifiedUser.DoesNotExist:
            return "N/A"

    def get_provider_role(self, obj):
        try:
            user = VerifiedUser.objects.get(auth_user_id=obj.auth_user_id)
            return user.role
        except VerifiedUser.DoesNotExist:
            return "Unknown Role"

    def get_document_type(self, obj):
        try:
            # Safely get definition_id
            def_id = getattr(obj, 'definition_id', None)
            if not def_id:
                return "Unknown Type (No ID)"

            definition = ProviderDocumentDefinition.objects.get(id=def_id)
            return definition.label
        except ProviderDocumentDefinition.DoesNotExist:
            return f"Unknown Type ({def_id})"
        except Exception:
            return "Error Resolving Type"

