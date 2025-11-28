

# admin_core/serializers.py
from rest_framework import serializers
from .models import SuperAdmin, VerifiedUser, AdminProfile, Permission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "description"]


class VerifiedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerifiedUser
        fields = [
            "id", "auth_user_id", "full_name", "email", "phone_number",
            "role", "permissions", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminProfileSerializer(serializers.ModelSerializer):
    # Represent verified_user by its auth_user_id and nested info for UI convenience.
    verified_user = serializers.SlugRelatedField(
        slug_field="auth_user_id",
        queryset=VerifiedUser.objects.all()
    )
    verified_user_info = VerifiedUserSerializer(source='verified_user', read_only=True)
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = AdminProfile
        fields = [
            "id", "verified_user", "verified_user_info",
            "department", "designation", "address", "profile_image",
            "activity_status", "is_deleted", "permissions",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "verified_user_info", "created_at", "updated_at"]


class AdminProfileUpdateSerializer(serializers.ModelSerializer):
    # allow updating profile fields only, not verified_user
    class Meta:
        model = AdminProfile
        fields = ["department", "designation", "address", "profile_image", "activity_status"]


class SuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = [
            "id", "auth_user_id", "email", "contact", "first_name",
            "last_name", "user_role", "is_active", "is_staff",
            "is_admin", "is_super_admin", "activity_status"
        ]
        read_only_fields = ["id", "auth_user_id", "email"]
