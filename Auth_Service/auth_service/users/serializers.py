
# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Permission, OTP, StoredRefreshToken,EmailTemplate
from uuid import uuid4
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


# ============================
# Role & Permission Serializers
# ============================
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'description']


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )
    permission_details = PermissionSerializer(source="permissions", many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "permission_details"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        role = Role.objects.create(**validated_data)
        role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance

# ============================
# User Registration Serializer
# ============================
class RegisterSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=True)
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.CharField(required=True)  # frontend sends role_id as string or number

    class Meta:
        model = User
        fields = ['phone_number', 'full_name', 'email', 'role']

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    # ------------------------------------------------------------------
    # FIXED CREATE METHOD (THIS IS THE IMPORTANT PART)
    # ------------------------------------------------------------------
    def create(self, validated_data):
        # Extract role_id coming from frontend (often a string)
        role_id = validated_data.pop("role", None)

        if not role_id:
            raise serializers.ValidationError({"role": "Role ID is required"})

        try:
            # Convert to int safely
            role_id = int(role_id)
        except ValueError:
            raise serializers.ValidationError({"role": "Role ID must be a number"})

        # Fetch the correct Role object (DO NOT CREATE NEW)
        try:
            role_obj = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            raise serializers.ValidationError({"role": f"Invalid role ID: {role_id}"})

        # Generate unique username
        username = f"user_{uuid4().hex[:10]}"

        # Create user
        user = User(
            id=uuid4(),
            username=username,
            phone_number=validated_data.get('phone_number'),
            full_name=validated_data.get('full_name'),
            email=validated_data.get('email') or None,
            role=role_obj,             # ✔ Correct role assignment
            is_active=False            # Activate after OTP
        )

        user.set_unusable_password()
        user.save()

        return user
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "phone_number",
            "role",
        ]
        read_only_fields = ["id", "username"]

# ============================
# OTP Serializers
# ============================
class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    purpose = serializers.ChoiceField(choices=['login', 'register', 'verify'], default='login')


class VerifyOTPSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)



# ============================
# User & Token Serializers
# ============================
class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone_number', 'email', 'role', 'role_name']


class StoredRefreshTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredRefreshToken
        fields = [
            'id', 'token_hash', 'created_at', 'expires_at',
            'revoked', 'user_agent', 'ip_address'
        ]


class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ['id', 'phone_number', 'otp', 'purpose', 'created_at', 'expires_at', 'used']





class EmailTemplateSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source="created_by.id")

    class Meta:
        model = EmailTemplate
        fields = [
            "id", "name", "role", "type", "subject", "html_content",
            "is_default", "is_active", "created_by", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class SendManualEmailSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    template_id = serializers.UUIDField()