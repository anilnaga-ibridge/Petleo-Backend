# from rest_framework import serializers
# from .models import (
#     LocalFieldDefinition,
#     ProviderFieldValue,
#     LocalDocumentDefinition,
#     ProviderDocument
# )


# # ==========================================================
# # FIELD DEFINITIONS
# # ==========================================================
# class LocalFieldDefinitionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LocalFieldDefinition
#         fields = "__all__"


# class ProviderFieldValueSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProviderFieldValue
#         fields = "__all__"
#         read_only_fields = ("id", "updated_at")


# class ProviderSubmitFieldSerializer(serializers.Serializer):
#     field_id = serializers.UUIDField()
#     value = serializers.JSONField(required=False)
#     metadata = serializers.JSONField(required=False)

#     def validate(self, data):
#         field_id = data["field_id"]
#         try:
#             field_def = LocalFieldDefinition.objects.get(id=field_id)
#         except LocalFieldDefinition.DoesNotExist:
#             raise serializers.ValidationError("Invalid field_id")

#         if field_def.is_required and not data.get("value"):
#             raise serializers.ValidationError(f"{field_def.label} is required")

#         return data


# # ==========================================================
# # DOCUMENTS
# # ==========================================================
# class LocalDocumentDefinitionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LocalDocumentDefinition
#         fields = "__all__"


# class ProviderDocumentSerializer(serializers.ModelSerializer):
#     file_url = serializers.SerializerMethodField()

#     class Meta:
#         model = ProviderDocument
#         fields = [
#             "id", "verified_user", "definition_id",
#             "filename", "content_type", "size",
#             "status", "notes", "file", "file_url",
#             "uploaded_at", "updated_at"
#         ]
#         read_only_fields = ("id", "status", "uploaded_at", "updated_at")

#     def get_file_url(self, obj):
#         request = self.context.get("request")
#         if obj.file and request:
#             return request.build_absolute_uri(obj.file.url)
#         return obj.file.url if obj.file else None
# class ProviderProfileSerializer(serializers.Serializer):
#     fields = serializers.ListField(child=serializers.DictField())
#     uploaded_documents = serializers.ListField(child=serializers.DictField())
#     requested_documents = serializers.ListField(child=serializers.DictField())
    
# from rest_framework import serializers
# from .models import LocalFieldDefinition, ProviderFieldValue, LocalDocumentDefinition, ProviderDocument


# class ProviderDocumentSerializer(serializers.ModelSerializer):
#     file_url = serializers.SerializerMethodField()

#     class Meta:
#         model = ProviderDocument
#         fields = [
#             "id", "definition_id", "filename",
#             "content_type", "size",
#             "status", "notes",
#             "file_url", "uploaded_at", "updated_at"
#         ]

#     def get_file_url(self, obj):
#         request = self.context.get("request")
#         if obj.file:
#             return request.build_absolute_uri(obj.file.url)
#         return None


# class ProviderProfileSerializer(serializers.Serializer):
#     fields = serializers.ListField()
#     uploaded_documents = serializers.ListField()
#     requested_documents = serializers.ListField()
# provider_dynamic_fields/serializers.py

from rest_framework import serializers
from .models import (
    LocalFieldDefinition,
    ProviderFieldValue,
    LocalDocumentDefinition,
    ProviderDocument
)


# ==========================================================
# LOCAL FIELD DEFINITIONS
# ==========================================================
class LocalFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalFieldDefinition
        fields = "__all__"


# ==========================================================
# PROVIDER FIELD VALUE (Profile fields)
# ==========================================================
class ProviderFieldValueSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProviderFieldValue
        fields = [
            "id",
            "verified_user",
            "field_id",
            "value",
            "metadata",
            "file",
            "file_url",
            "updated_at"
        ]
        read_only_fields = ("id", "updated_at")

    def get_file_url(self, obj):
        """Return full absolute file URL."""
        if obj.file and hasattr(obj.file, "url"):
            request = self.context.get("request")
            if request is not None:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


# ==========================================================
# FIELD SUBMIT SERIALIZER (text fields only)
# ==========================================================
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

        # Required text fields
        if field_def.field_type != "file":
            if field_def.is_required and (data.get("value") in [None, "", []]):
                raise serializers.ValidationError(f"{field_def.label} is required")

        return data


# ==========================================================
# DOCUMENT DEFINITIONS (Requested docs)
# ==========================================================
class LocalDocumentDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalDocumentDefinition
        fields = "__all__"


# ==========================================================
# PROVIDER DOCUMENTS (Requested doc uploads)
# ==========================================================
class ProviderDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProviderDocument
        fields = [
            "id",
            "definition_id",
            "filename",
            "content_type",
            "size",
            "status",
            "notes",
            "file_url",
            "uploaded_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        """Return full absolute URL for document files."""
        if obj.file and hasattr(obj.file, "url"):
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


# ==========================================================
# PROFILE RESPONSE SERIALIZER
# (fields + uploaded_docs + requested_docs)
# ==========================================================
class ProviderProfileSerializer(serializers.Serializer):
    """
    Used only to structure GET response of combined profile API.
    """
    fields = serializers.ListField()
    uploaded_documents = serializers.ListField()
    requested_documents = serializers.ListField()
