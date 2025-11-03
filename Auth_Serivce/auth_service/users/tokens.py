from rest_framework_simplejwt.tokens import RefreshToken


# def get_tokens_for_user(user, request=None):
#     """
#     Returns a dictionary with access and refresh tokens for the given user.
#     """
#     refresh = RefreshToken.for_user(user)

#     # Optional: include extra info in payload
#     refresh['username'] = user.username
#     refresh['role'] = getattr(user, 'role', 'user')

#     return {
#         'refresh': str(refresh),
#         'access': str(refresh.access_token)
#     }


# def get_tokens_for_user(user):
#     refresh = RefreshToken.for_user(user)
#     return {
#         "refresh": str(refresh),
#         "access": str(refresh.access_token),
#     }

# def get_tokens_for_user(user):
#     refresh = RefreshToken.for_user(user)
#     return {
#         'refresh': str(refresh),
#         'access': str(refresh.access_token),
#     }
# tokens.py (or wherever you generate JWT)
# from rest_framework_simplejwt.tokens import RefreshToken

# def get_tokens_for_user(user):
#     refresh = RefreshToken.for_user(user)
#     refresh['role'] = user.role.name if user.role else None
#     refresh['permissions'] = list(user.role.permissions.values_list('codename', flat=True)) if user.role else []
#     refresh['token_version'] = user.token_version
#     return {
#         'refresh': str(refresh),
#         'access': str(refresh.access_token),
#     }


# ==================================================================================
# from rest_framework_simplejwt.tokens import RefreshToken

# def get_tokens_for_user(user):
#     refresh = RefreshToken.for_user(user)
#     # override payload to store UUID as string and include user info
#     refresh['user_id'] = str(user.id)
#     refresh['username'] = user.username
#     refresh['email'] = user.email
#     refresh['is_superuser'] = user.is_superuser
#     refresh['role'] = user.role.name if user.role else None
#     return {
#         'refresh': str(refresh),
#         'access': str(refresh.access_token),
#     }


# ==========================================phone otp===========================
# auth_service/tokens.py
# users/tokens.py
import hashlib
from uuid import uuid4
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import StoredRefreshToken
from rest_framework_simplejwt.tokens import RefreshToken

REFRESH_TTL_DAYS = int(getattr(settings, 'REFRESH_TTL_DAYS', 14))
REFRESH_EXPIRES_DELTA = timedelta(days=REFRESH_TTL_DAYS)

def _hash_token(token_plain: str) -> str:
    return hashlib.sha256(token_plain.encode('utf-8')).hexdigest()

def create_refresh_token_for_user(user, request=None):
    """
    Create opaque refresh token (UUID) for client, store hashed in DB, return plain token.
    """
    token_plain = uuid4().hex + uuid4().hex  # 64+ hex string
    token_hash = _hash_token(token_plain)
    now = timezone.now()
    expires_at = now + REFRESH_EXPIRES_DELTA

    ip = None
    ua = None
    if request is not None:
        ip = request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT')

    StoredRefreshToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=(ua[:255] if ua else None),
        ip_address=(ip[:45] if ip else None)
    )
    return token_plain

def verify_and_rotate_refresh_token(token_plain: str, request=None):
    """
    Verify token exists and not revoked/expired. If valid, revoke old and create + return new tokens.
    Returns user, new_refresh_plain or raises ValueError.
    """
    token_hash = _hash_token(token_plain)
    try:
        stored = StoredRefreshToken.objects.get(token_hash=token_hash, revoked=False)
    except StoredRefreshToken.DoesNotExist:
        raise ValueError("Invalid refresh token")

    if stored.is_expired():
        stored.revoked = True
        stored.save(update_fields=['revoked'])
        raise ValueError("Refresh token expired")

    user = stored.user
    # revoke current
    stored.revoked = True
    stored.save(update_fields=['revoked'])

    # create new
    new_plain = create_refresh_token_for_user(user, request=request)
    # create new access jwt
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    return user, access, new_plain



def get_tokens_for_user(user, request=None):

    refresh = RefreshToken.for_user(user)

    # Basic user info
    refresh['role'] = user.role.name if user.role else None
    refresh['phone_number'] = user.phone_number
    refresh['full_name'] = user.full_name
    refresh['is_superuser'] = user.is_superuser

    # Permissions
    if user.role:
        permissions = list(user.role.permissions.values_list('codename', flat=True))
    else:
        permissions = []

    refresh['permissions'] = permissions

    # Same data inside access token
    access_token = refresh.access_token
    access_token['role'] = refresh['role']
    access_token['permissions'] = permissions

    return {
        'refresh': str(refresh),
        'access': str(access_token),
    }
