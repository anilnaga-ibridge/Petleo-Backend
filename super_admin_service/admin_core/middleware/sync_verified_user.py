import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from admin_core.models import VerifiedUser
import logging

logger = logging.getLogger(__name__)


class SyncVerifiedUserMiddleware(MiddlewareMixin):
    """
    Middleware that ensures the VerifiedUser from Auth Service exists locally.
    Optimized: Avoids update_or_create on every request.
    """
    PUBLIC_KEYWORD = "/definitions/public"

    def process_request(self, request):
        if self.PUBLIC_KEYWORD in request.path or request.path.startswith("/api/superadmin/definitions/public"):
            return

        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Bearer "):
            return

        token = auth_header.split("Bearer ")[1]

        try:
            # We use a fast check here. If the user is already in the request, skip.
            # Usually CentralAuthJWTAuthentication already sets request.user
            payload = jwt.decode(token, settings.AUTH_PUBLIC_KEY, algorithms=["RS256"])
        except Exception:
            return 

        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            return

        # 🔥 Optimization: Only create if it doesn't exist. 
        # Updates should be handled by Kafka to keep requests fast.
        if not VerifiedUser.objects.filter(auth_user_id=user_id).exists():
            defaults = {
                "email": payload.get("email", ""),
                "full_name": payload.get("full_name", ""),
                "role": payload.get("role", ""),
                "phone_number": payload.get("phone_number", ""),
            }
            VerifiedUser.objects.create(auth_user_id=user_id, **defaults)
        
        # We don't necessarily need to attach it to request here if DRF does it, 
        # but keep it if other parts of the system expect request.verified_user
        try:
            request.verified_user = VerifiedUser.objects.get(auth_user_id=user_id)
        except VerifiedUser.DoesNotExist:
            pass
