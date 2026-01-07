
import jwt
import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import os

logger = logging.getLogger(__name__)
User = get_user_model()

logger.warning("⚠ Using authentication.py at: " + os.path.abspath(__file__))
import logging



class CentralAuthJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Auth for all microservices
    """

    PUBLIC_KEYWORD = "/definitions/public"
    PUBLIC_PATHS = [
    "/api/superadmin/definitions/public",
    "/api/superadmin/definitions/public/",
    "/api/superadmin/provider/plans/",
    # "/api/superadmin/services/",  <-- REMOVED THIS to enable auth
    ]


    def authenticate(self, request):
        request_path = request.path
        logging.warning(f"🟥 AUTHENTICATION CALLED — PATH: {request.path}")
        # --------------------------
        # ✔ PUBLIC ENDPOINT BYPASS
        # --------------------------
        for path in self.PUBLIC_PATHS:
            if request_path.startswith(path):
                logger.warning(f"🔓 PUBLIC AUTH BYPASS: {request_path}")
                return None


        # ✔ Debug logs OUTSIDE loop
        logger.warning(f"📌 Incoming secured path = {request_path}")
        # print("🔥 AUTH MODULE LOADED:", __file__)

        # --------------------------
        # ✔ Normal JWT Auth
        # --------------------------
        auth_header = self.get_header(request)
        if auth_header is None:
            logger.warning(f"🔒 Missing Authorization header on PROTECTED URL: {request_path}")
            # raise AuthenticationFailed(_("Unauthorized"), code="authorization_header_missing")
            return None # Allow DRF to handle missing auth (e.g. for IsAuthenticatedOrReadOnly)

        raw_token = self.get_raw_token(auth_header)
        if raw_token is None:
            # raise AuthenticationFailed(_("Unauthorized"), code="token_missing")
             return None

        try:
            payload = jwt.decode(
                raw_token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )

            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)

            logger.info(f"✅ Authenticated user {user} | role = {getattr(user, 'user_role', None)}")
            return (user, validated_token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed(_("Token expired"), code="token_expired")

        except jwt.InvalidTokenError:
            raise AuthenticationFailed(_("Invalid token"), code="invalid_token")

        except Exception as e:
            logger.error(f"❌ Authentication error: {str(e)}")
            raise AuthenticationFailed(_("Authentication failed"), code="auth_failed")

    def get_user(self, validated_token):
        user_id = validated_token.get("user_id")
        email = validated_token.get("email")
        role = validated_token.get("role", "").lower()

        if not user_id:
            raise AuthenticationFailed(_("Token missing user_id claim"), code="no_user_id")

        try:
            user = User.objects.get(auth_user_id=user_id)

        except User.DoesNotExist:
            # Shadow local user
            user = User.objects.create(
                auth_user_id=user_id,
                email=email or f"auto_{user_id}@central-auth.local",
                first_name=(validated_token.get("full_name") or "").split(" ")[0],
                last_name=(validated_token.get("full_name") or "").split(" ")[-1],
                user_role=role,
                is_active=True,
                is_staff=True,
                is_admin=(role in ["admin", "superadmin"]),
                is_super_admin=(role == "superadmin"),
                activity_status="active",
            )

        # keep roles updated
        if user.user_role != role:
            user.user_role = role
            user.is_super_admin = (role == "superadmin")
            user.is_admin = (role in ["admin", "superadmin"])
            user.save()

        return user
