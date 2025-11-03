
# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# from django.contrib.auth.hashers import make_password
# from django.contrib.auth import authenticate

# User = get_user_model()

# # Registration serializer
# class UserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)

#     class Meta:
#         model = User
#         fields = ["id", "username", "email", "password"]

   
#     def create(self, validated_data):
#         password = validated_data.pop('password')
#         user = User(**validated_data)
#         user.set_password(password)  # <-- HASH the password
#         user.save()
#         return user


# # Login serializer
# class LoginSerializer(serializers.Serializer):
#     username = serializers.CharField()
#     password = serializers.CharField(write_only=True)

#     def validate(self, data):
#         user = authenticate(username=data.get('username'), password=data.get('password'))
#         if not user:
#             raise serializers.ValidationError("Invalid credentials")
#         if not user.is_active:
#             raise serializers.ValidationError("User is inactive")
#         data['user'] = user
#         return data


# ==============================================================================================
# from rest_framework import serializers
# from django.contrib.auth import authenticate
# from .models import User, Role, Permission
# import random
# from django.contrib.auth import get_user_model
# import string
# # # --- User Registration & Login ---
# # class RegisterSerializer(serializers.ModelSerializer):
# #     class Meta:
# #         model = User
# #         fields = ['username', 'email', 'password', 'role']
# #         extra_kwargs = {'password': {'write_only': True}}

# #     def create(self, validated_data):
# #         password = validated_data.pop('password')
# #         user = User(**validated_data)
# #         user.set_password(password)
# #         user.save()
# #         return user

# User = get_user_model()

# def generate_random_password(length=12):
#     chars = string.ascii_letters + string.digits + string.punctuation
#     return ''.join(random.choice(chars) for _ in range(length))

# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(
#         write_only=True, 
#         required=False,  # password is now optional
#         allow_blank=True  # allow empty string
#     )

#     class Meta:
#         model = User
#         fields = ['username', 'email', 'password', 'role']

#     def create(self, validated_data):
#         # Get password if provided, else generate one
#         password = validated_data.pop('password', None)
#         if not password:  # covers None or empty string
#             password = generate_random_password()

#         user = User(**validated_data)
#         user.set_password(password)
#         user.save()

#         # Attach generated password for sending email or Kafka if needed
#         user.generated_password = password  
#         return user
# class LoginSerializer(serializers.Serializer):
#     username = serializers.CharField()
#     password = serializers.CharField(write_only=True)

#     def validate(self, data):
#         user = authenticate(username=data.get('username'), password=data.get('password'))
#         if not user:
#             raise serializers.ValidationError("Invalid credentials")
#         if not user.is_active:
#             raise serializers.ValidationError("User is inactive")
#         data['user'] = user
#         return data


# # --- Role & Permission Serializers ---
# class PermissionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Permission
#         fields = ['id', 'codename', 'description']


# class RoleSerializer(serializers.ModelSerializer):
#     permissions = PermissionSerializer(many=True, read_only=True)

#     class Meta:
#         model = Role
#         fields = ['id', 'name', 'description', 'permissions']


# class RoleCreateSerializer(serializers.ModelSerializer):
#     permission_ids = serializers.ListField(
#         child=serializers.IntegerField(), write_only=True, required=False
#     )

#     class Meta:
#         model = Role
#         fields = ['name', 'description', 'permission_ids']

#     def create(self, validated_data):
#         permission_ids = validated_data.pop('permission_ids', [])
#         role = Role.objects.create(**validated_data)
#         if permission_ids:
#             role.permissions.set(permission_ids)
#         return role
# class UserSerializer(serializers.ModelSerializer):
#     role_name = serializers.CharField(source='role.name', read_only=True)

#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'role', 'role_name', 'is_active']
#         read_only_fields = ['id']
# class UpdatePasswordSerializer(serializers.Serializer):
#     old_password = serializers.CharField(write_only=True)
#     new_password = serializers.CharField(write_only=True)


# ======================================================phone Number otp==============
# auth_service/serializers.py
# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Permission, OTP, StoredRefreshToken
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

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        role = Role.objects.create(**validated_data)
        if permissions:
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
    role = serializers.CharField(required=False, allow_blank=True)

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

    def create(self, validated_data):
        # Handle Role (create or get existing)
        role_name = validated_data.pop('role', None)
        role_obj = None
        if role_name:
            role_obj, _ = Role.objects.get_or_create(name=role_name)

        # Generate unique username
        username = f"user_{uuid4().hex[:10]}"

        user = User(
            id=uuid4(),
            username=username,
            phone_number=validated_data.get('phone_number'),
            full_name=validated_data.get('full_name'),
            email=validated_data.get('email') or None,
            role=role_obj,
            is_active=False  # Activate only after OTP verify
        )
        user.set_unusable_password()
        user.save()
        return user


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
