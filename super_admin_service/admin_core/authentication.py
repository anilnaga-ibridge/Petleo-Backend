# # admin_core/authentication.py
# from rest_framework_simplejwt.authentication import JWTAuthentication
# from rest_framework import exceptions

# class SimpleUser:
#     """
#     Simple user class to hold JWT token data
#     """
#     def __init__(self, user_id, role=None):
#         self.id = user_id  # This can be a UUID string
#         self.user_id = user_id
#         self.role = role
#         self.is_authenticated = True
#         self.is_anonymous = False
#         self.is_active = True

# class AuthServiceJWTAuthentication(JWTAuthentication):
#     """
#     Authenticate JWT issued by Auth Service and create a simple user object
#     """
#     def get_user(self, validated_token):
#         """
#         Instead of looking up DB, create a dummy user from token
#         """
#         user_id = validated_token.get("user_id")
#         role = validated_token.get("role", None)
        
#         # Create a simple user object that can handle UUID IDs
#         user = SimpleUser(user_id=user_id, role=role)
#         return user
# admin_core/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class CentralAuthJWTAuthentication(JWTAuthentication):
    """
    ✅ Authenticates JWTs issued by the Central Auth Service.
    ✅ Automatically syncs user info (auth_user_id, email, role).
    ✅ Works across all microservices.
    """

    def get_user(self, validated_token):
        """
        Extract user_id and role from token claims, then map or create the local user.
        """
        user_id = validated_token.get("user_id")
        email = validated_token.get("email")
        role = validated_token.get("role", "").lower()

        if not user_id:
            raise AuthenticationFailed(_("Token missing user_id claim."), code="no_user_id")

        try:
            user = User.objects.get(auth_user_id=user_id)
        except User.DoesNotExist:
            # Auto-create the local shadow user record (without password)
            logger.info(f"Creating local shadow SuperAdmin for Auth User ID: {user_id}")
            user = User.objects.create(
                auth_user_id=user_id,
                email=email or f"auto_{user_id}@central-auth.local",
                first_name=validated_token.get("full_name", "").split(" ")[0] if validated_token.get("full_name") else "",
                last_name=validated_token.get("full_name", "").split(" ")[1] if validated_token.get("full_name") and " " in validated_token.get("full_name") else "",
                user_role=role or "superadmin",
                is_active=True,
                is_staff=True,
                is_admin=(role in ["admin", "superadmin"]),
                is_super_admin=(role == "superadmin"),
                activity_status="active",
            )

        # Update the role if token role changed
        token_role = role or "superadmin"
        if user.user_role != token_role:
            user.user_role = token_role
            user.is_super_admin = (token_role == "superadmin")
            user.is_admin = (token_role in ["admin", "superadmin"])
            user.save(update_fields=["user_role", "is_super_admin", "is_admin"])

        return user
