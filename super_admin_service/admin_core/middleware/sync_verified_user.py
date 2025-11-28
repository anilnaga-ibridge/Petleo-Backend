import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from admin_core.models import VerifiedUser
import logging

logger = logging.getLogger(__name__)


class SyncVerifiedUserMiddleware(MiddlewareMixin):
    """
    Middleware that ensures the VerifiedUser from Auth Service exists locally
    for every authenticated request.
    """
    PUBLIC_KEYWORD = "/definitions/public"
    def process_request(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if request.path.startswith("/api/superadmin/definitions/public"):
            return
        logger.warning(f"🟦 SyncMiddleware HIT — PATH: {request.path}")
        if self.PUBLIC_KEYWORD in request.path:
            logger.warning(f"⏭ MIDDLEWARE SKIP PUBLIC: {request.path}")
            return
        if not auth_header or not auth_header.startswith("Bearer "):
            return

        token = auth_header.split("Bearer ")[1]

        try:
            payload = jwt.decode(token, settings.AUTH_PUBLIC_KEY, algorithms=["RS256"])
        except Exception:
            return  # invalid or expired token – let DRF handle auth errors

        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            return

        defaults = {
            "email": payload.get("email", ""),
            "full_name": payload.get("full_name", ""),
            "role": payload.get("role", ""),
            "phone_number": payload.get("phone_number", ""),
            "is_verified": True,
        }

        VerifiedUser.objects.update_or_create(
            auth_user_id=user_id, defaults=defaults
        )

        request.verified_user = VerifiedUser.objects.get(auth_user_id=user_id)
def process_request(self, request):
    import logging
    logging.warning("🟦 MIDDLEWARE HIT: " + request.path)
