
# admin_core/serializers.py
from rest_framework import serializers
from .models import SuperAdmin,VerifiedUser
from .models import AdminProfile,  Permission
class SuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = [
            "id", "auth_user_id", "email", "contact", "first_name",
            "last_name", "user_role", "is_active", "is_staff",
            "is_admin", "is_super_admin", "activity_status"
        ]
        read_only_fields = ["id", "auth_user_id", "email"]

# Optional: For partial update
class SuperAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = [
            "contact", "first_name", "last_name", "user_role", 
            "is_active", "is_staff", "is_admin", "activity_status"
        ]
class VerifiedUserSerializer(serializers.ModelSerializer):
    # Explicitly define auth_user_id to ensure UUID validation works smoothly
    auth_user_id = serializers.UUIDField(required=True)

    class Meta:
        model = VerifiedUser
        fields = [
            "id",
            "auth_user_id",
            "full_name",
            "email",
            "phone_number",
            "role",
            "permissions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "description"]


# class AdminProfileSerializer(serializers.ModelSerializer):
#     verified_user = serializers.StringRelatedField()
#     permissions = PermissionSerializer(many=True, read_only=True)

#     class Meta:
#         model = AdminProfile
#         fields = [
#             "id", "verified_user", "department", "designation",
#             "address", "profile_image", "activity_status",
#             "permissions", "created_at", "updated_at"
#         ]


class AdminProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ["department", "designation", "address", "profile_image", "activity_status"]
        
class AdminProfileSerializer(serializers.ModelSerializer):
    verified_user = serializers.SlugRelatedField(
        slug_field="auth_user_id",
        queryset=VerifiedUser.objects.all().values("auth_user_id", "email", "role")
    )

    class Meta:
        model = AdminProfile
        fields = "__all__"