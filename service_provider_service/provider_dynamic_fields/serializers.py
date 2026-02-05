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


# ==========================================================
# 6) PROVIDER CRUD SERIALIZERS
# ==========================================================
from .models import ProviderCategory, ProviderFacility, ProviderPricing

class ProviderCategorySerializer(serializers.ModelSerializer):
    facilities = serializers.SerializerMethodField()

    class Meta:
        model = ProviderCategory
        fields = ["id", "service_id", "name", "is_active", "created_at", "facilities"]
        read_only_fields = ["id", "created_at"]

    def get_facilities(self, obj):
        from .models import ProviderFacility
        facilities = obj.facilities.filter(is_active=True)
        return ProviderFacilitySerializer(facilities, many=True).data

class ProviderFacilitySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ProviderFacility
        fields = ["id", "category", "category_name", "name", "description", "price", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

class ProviderPricingSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    facility_description = serializers.CharField(source="facility.description", read_only=True)
    # We need to fetch category name. Since category_id is CharField (not FK), we can't use source="category.name".
    # But wait, ProviderPricing.category_id stores the ID. 
    # If it's a ProviderCategory, we can look it up.
    # If it's a SuperAdmin category, we can't easily look it up here without a query.
    # However, for Provider CRUD, we are mostly dealing with ProviderCategories.
    # Let's add a SerializerMethodField.
    category_name = serializers.SerializerMethodField()

    duration = serializers.IntegerField(source="duration_minutes", required=False, allow_null=True)

    class Meta:
        model = ProviderPricing
        fields = ["id", "service_id", "category_id", "category_name", "facility", "facility_name", "facility_description", "price", "billing_unit", "duration", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_category_name(self, obj):
        if not obj.category_id:
            return None
        # Try to find ProviderCategory
        from .models import ProviderCategory
        try:
            cat = ProviderCategory.objects.get(id=obj.category_id)
            return cat.name
        except:
            return "Unknown Category"
