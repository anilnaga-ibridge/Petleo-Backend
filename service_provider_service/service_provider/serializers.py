from rest_framework import serializers
from .models import ServiceProvider, BusinessDetails, DocumentVerification, VerificationWorkflow
import re
from .models import Document
from .models import ProviderDocument 
from .models import DocumentVerificationCategory, AutoVerificationLog
# service_provider/serializers.py
from service_provider.models import VerifiedUser
class ServiceProviderSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='verified_user.full_name', read_only=True)
    email = serializers.EmailField(source='verified_user.email', read_only=True)
    phone_number = serializers.CharField(source='verified_user.phone_number', read_only=True)
    role = serializers.CharField(source='verified_user.role', read_only=True)

    class Meta:
        model = ServiceProvider
        fields = ['id', 'full_name', 'email', 'phone_number', 'role', 'profile_status', 'avatar', 'is_fully_verified']


class BusinessDetailsSerializer(serializers.ModelSerializer):
    auth_user_id = serializers.UUIDField(write_only=True)
    service_provider_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = BusinessDetails
        fields = [
            "id",
            "auth_user_id",
            "service_provider_id",
            "business_name",
            "business_type",
            "business_description",
            "gst_number",
            "pan_number",
            "address",
            "city",
            "state",
            "pincode",
            "is_business_verified",
            "verified_at",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "verified_at"]

    # ✅ Validate GST number
    def validate_gst_number(self, value):
        if value and not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', value):
            raise serializers.ValidationError("Invalid GSTIN format. Example: 27ABCDE1234F1ZV")
        return value

    # ✅ Validate PAN number
    def validate_pan_number(self, value):
        if value and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', value):
            raise serializers.ValidationError("Invalid PAN format. Example: ABCDE1234F")
        return value

    # ✅ Create logic
    def create(self, validated_data):
        auth_user_id = validated_data.pop("auth_user_id")
        service_provider_id = validated_data.pop("service_provider_id")

        # Fetch linked objects
        verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        service_provider = ServiceProvider.objects.get(id=service_provider_id)

        # Remove potential duplicates
        validated_data.pop("verified_user", None)
        validated_data.pop("service_provider", None)

        # Create new business record
        business = BusinessDetails.objects.create(
            verified_user=verified_user,
            service_provider=service_provider,
            **validated_data
        )

        return business
    
    
    
class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Handles document upload and verification."""
    class Meta:
        model = DocumentVerification
        fields = [
            'id', 'verified_user', 'service_provider',
            'aadhar_card', 'business_license', 'pan_card', 'gst_certificate',
            'is_verified', 'verified_by', 'verified_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'verified_user', 'service_provider',
            'is_verified', 'verified_by', 'verified_at', 'created_at', 'updated_at'
        ]


class VerificationWorkflowSerializer(serializers.ModelSerializer):
    """Handles verification stage tracking."""
    class Meta:
        model = VerificationWorkflow
        fields = [
            'id', 'verified_user', 'service_provider',
            'manual_verification', 'automated_verification', 'verified_stage', 'last_updated'
        ]
        read_only_fields = ['id', 'verified_user', 'service_provider', 'last_updated']






class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'document_name', 'is_mandatory', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']  # The ID and created_at should be read-only

class DocumentVerificationCategorySerializer(serializers.ModelSerializer):
    documents = serializers.PrimaryKeyRelatedField(queryset=Document.objects.all(), many=True)

    class Meta:
        model = DocumentVerificationCategory
        fields = ['id', 'service_type', 'documents', 'created_at']

    def create(self, validated_data):
        # Extract documents from validated data
        documents_data = validated_data.pop('documents')
        
        # Create the DocumentVerificationCategory object
        category = DocumentVerificationCategory.objects.create(**validated_data)
        
        # Associate documents with the category
        category.documents.set(documents_data)  # Set the documents using the related field
        
        # Save and return the category
        category.save()
        return category

class ProviderDocumentSerializer(serializers.ModelSerializer):
    file_size = serializers.CharField(required=False)
    verified_by = serializers.CharField(required=False)
    verified_at = serializers.DateTimeField(required=False)
    
    class Meta:
        model = ProviderDocument
        fields = [
            'id', 'verified_user', 'service_provider', 'category', 'file',
            'file_size', 'verification_status', 'remarks', 'verified_by',
            'verified_at', 'expiry_date', 'created_at', 'updated_at'
        ]


class AutoVerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoVerificationLog
        fields = ['id', 'provider_document', 'verification_source', 'response_status', 'response_data', 'verified_at']