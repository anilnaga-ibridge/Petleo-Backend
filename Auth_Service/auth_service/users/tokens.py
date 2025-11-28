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


# # ==========================================phone otp===========================
# # auth_service/tokens.py
# # users/tokens.py
# import hashlib
# from uuid import uuid4
# from django.utils import timezone
# from datetime import timedelta
# from django.conf import settings
# from .models import StoredRefreshToken
# from rest_framework_simplejwt.tokens import RefreshToken

# REFRESH_TTL_DAYS = int(getattr(settings, 'REFRESH_TTL_DAYS', 14))
# REFRESH_EXPIRES_DELTA = timedelta(days=REFRESH_TTL_DAYS)

# def _hash_token(token_plain: str) -> str:
#     return hashlib.sha256(token_plain.encode('utf-8')).hexdigest()

# def create_refresh_token_for_user(user, request=None):
#     """
#     Create opaque refresh token (UUID) for client, store hashed in DB, return plain token.
#     """
#     token_plain = uuid4().hex + uuid4().hex  # 64+ hex string
#     token_hash = _hash_token(token_plain)
#     now = timezone.now()
#     expires_at = now + REFRESH_EXPIRES_DELTA

#     ip = None
#     ua = None
#     if request is not None:
#         ip = request.META.get('REMOTE_ADDR')
#         ua = request.META.get('HTTP_USER_AGENT')

#     StoredRefreshToken.objects.create(
#         user=user,
#         token_hash=token_hash,
#         expires_at=expires_at,
#         user_agent=(ua[:255] if ua else None),
#         ip_address=(ip[:45] if ip else None)
#     )
#     return token_plain

# def verify_and_rotate_refresh_token(token_plain: str, request=None):
#     """
#     Verify token exists and not revoked/expired. If valid, revoke old and create + return new tokens.
#     Returns user, new_refresh_plain or raises ValueError.
#     """
#     token_hash = _hash_token(token_plain)
#     try:
#         stored = StoredRefreshToken.objects.get(token_hash=token_hash, revoked=False)
#     except StoredRefreshToken.DoesNotExist:
#         raise ValueError("Invalid refresh token")

#     if stored.is_expired():
#         stored.revoked = True
#         stored.save(update_fields=['revoked'])
#         raise ValueError("Refresh token expired")

#     user = stored.user
#     # revoke current
#     stored.revoked = True
#     stored.save(update_fields=['revoked'])

#     # create new
#     new_plain = create_refresh_token_for_user(user, request=request)
#     # create new access jwt
#     refresh = RefreshToken.for_user(user)
#     access = str(refresh.access_token)
#     return user, access, new_plain



# def get_tokens_for_user(user, request=None):

#     refresh = RefreshToken.for_user(user)

#     # Basic user info
#     refresh['role'] = user.role.name if user.role else None
#     refresh['phone_number'] = user.phone_number
#     refresh['full_name'] = user.full_name
#     refresh['is_superuser'] = user.is_superuser

#     # Permissions
#     if user.role:
#         permissions = list(user.role.permissions.values_list('codename', flat=True))
#     else:
#         permissions = []

#     refresh['permissions'] = permissions

#     # Same data inside access token
#     access_token = refresh.access_token
#     access_token['role'] = refresh['role']
#     access_token['permissions'] = permissions

#     return {
#         'refresh': str(refresh),
#         'access': str(access_token),
#     }


# import hashlib
# from uuid import uuid4
# from datetime import timedelta
# from django.utils import timezone
# from django.conf import settings
# from rest_framework_simplejwt.tokens import RefreshToken
# from .models import StoredRefreshToken

# # Default refresh token lifetime (in days)
# REFRESH_TTL_DAYS = int(getattr(settings, 'REFRESH_TTL_DAYS', 14))
# REFRESH_EXPIRES_DELTA = timedelta(days=REFRESH_TTL_DAYS)


# # ------------------------------------------------------------
# # 🔹 Token hashing utility
# # ------------------------------------------------------------
# def _hash_token(token_plain: str) -> str:
#     """Hash a token string using SHA256 for secure DB storage."""
#     return hashlib.sha256(token_plain.encode('utf-8')).hexdigest()


# # ------------------------------------------------------------
# # 🔹 Create opaque (UUID-based) refresh token stored in DB
# # ------------------------------------------------------------
# def create_refresh_token_for_user(user, request=None, remember_me=False):
#     """
#     Create opaque refresh token (UUID-based), store hashed in DB,
#     and return the plain token for client storage.
#     """
#     token_plain = uuid4().hex + uuid4().hex  # 64-char random token
#     token_hash = _hash_token(token_plain)

#     now = timezone.now()
#     expires_at = now + timedelta(days=(30 if remember_me else REFRESH_TTL_DAYS))

#     ip = None
#     ua = None
#     if request is not None:
#         ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
#         ua = request.META.get("HTTP_USER_AGENT")

#     StoredRefreshToken.objects.create(
#         user=user,
#         token_hash=token_hash,
#         expires_at=expires_at,
#         user_agent=(ua[:255] if ua else None),
#         ip_address=(ip[:45] if ip else None),
#     )

#     return token_plain


# # ------------------------------------------------------------
# # 🔹 Verify + rotate refresh token
# # ------------------------------------------------------------
# def verify_and_rotate_refresh_token(token_plain: str, request=None):
#     """
#     Verify an opaque refresh token. If valid and not revoked,
#     revoke old token, issue a new one, and return:
#     (user, new_access_jwt, new_refresh_plain).
#     """
#     token_hash = _hash_token(token_plain)

#     try:
#         stored = StoredRefreshToken.objects.get(token_hash=token_hash, revoked=False)
#     except StoredRefreshToken.DoesNotExist:
#         raise ValueError("Invalid refresh token")

#     if stored.is_expired():
#         stored.revoked = True
#         stored.save(update_fields=["revoked"])
#         raise ValueError("Refresh token expired")

#     user = stored.user

#     # Revoke old token
#     stored.revoked = True
#     stored.save(update_fields=["revoked"])

#     # Create new opaque refresh token
#     new_plain = create_refresh_token_for_user(user, request=request)

#     # Create new JWT access token
#     refresh = RefreshToken.for_user(user)
#     access = str(refresh.access_token)

#     return user, access, new_plain


# # ------------------------------------------------------------
# # 🔹 Create JWT access/refresh pair
# # ------------------------------------------------------------
# def get_tokens_for_user(user, request=None, remember_me=False):
#     """
#     Generate JWT access + refresh tokens for a user.
#     Supports 'remember_me' to extend session lifetime.
#     """
#     refresh = RefreshToken.for_user(user)

#     # Adjust expiry dynamically based on remember_me
#     if remember_me:
#         refresh.set_exp(lifetime=timedelta(days=30))  # 30 days for remember me
#     else:
#         refresh.set_exp(lifetime=timedelta(hours=1))  # 1 hour for normal login

#     # Add custom claims to refresh token
#     refresh["role"] = user.role.name if user.role else None
#     refresh["phone_number"] = user.phone_number
#     refresh["full_name"] = user.full_name
#     refresh["is_superuser"] = user.is_superuser
#     refresh["iss"] = "django_issuer"
#     # Add permissions if user has a role
#     if user.role:
#         permissions = list(user.role.permissions.values_list("codename", flat=True))
#     else:
#         permissions = []

#     refresh["permissions"] = permissions

#     # Mirror custom claims into access token
#     access_token = refresh.access_token
#     access_token["role"] = refresh["role"]
#     access_token["permissions"] = permissions
#     access_token["iss"] = "django_issuer"
#     # Optional: shorter access lifetime
#     access_token.set_exp(lifetime=timedelta(minutes=15))

#     # Create and store an opaque refresh token (UUID-based)
#     opaque_token_plain = create_refresh_token_for_user(
#         user, request=request, remember_me=remember_me
#     )

#     return {
#         "access": str(access_token),
#         "refresh": str(refresh),
#         "opaque_refresh_token": opaque_token_plain,
#         "remember_me": remember_me,
#     }


# # ------------------------------------------------------------
# # 🔹 Optional cleanup utility (call via cron/command)
# # ------------------------------------------------------------
# def cleanup_expired_refresh_tokens():
#     """Delete expired or revoked refresh tokens from DB."""
#     now = timezone.now()
#     StoredRefreshToken.objects.filter(revoked=True).delete()
#     StoredRefreshToken.objects.filter(expires_at__lt=now).delete()




import hashlib
from uuid import uuid4
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from .models import StoredRefreshToken


# Default opaque refresh TTL (in days)
REFRESH_TTL_DAYS = int(getattr(settings, 'REFRESH_TTL_DAYS', 14))
REFRESH_EXPIRES_DELTA = timedelta(days=REFRESH_TTL_DAYS)


# ------------------------------------------------------------
# 🔹 Hash token before DB storage
# ------------------------------------------------------------
def _hash_token(token_plain: str) -> str:
    return hashlib.sha256(token_plain.encode('utf-8')).hexdigest()


# ------------------------------------------------------------
# 🔹 Create opaque refresh token (UUID-based)
# ------------------------------------------------------------
def create_refresh_token_for_user(user, request=None, remember_me=False):
    token_plain = uuid4().hex + uuid4().hex  # 64-char secure random string
    token_hash = _hash_token(token_plain)

    now = timezone.now()
    expires_at = now + timedelta(days=(30 if remember_me else REFRESH_TTL_DAYS))

    ip = None
    ua = None
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
        ua = request.META.get("HTTP_USER_AGENT")

    StoredRefreshToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=(ua[:255] if ua else None),
        ip_address=(ip[:45] if ip else None),
    )

    return token_plain


# ------------------------------------------------------------
# 🔹 Verify + rotate opaque refresh token
# ------------------------------------------------------------
def verify_and_rotate_refresh_token(token_plain: str, request=None):
    token_hash = _hash_token(token_plain)

    try:
        stored = StoredRefreshToken.objects.get(token_hash=token_hash, revoked=False)
    except StoredRefreshToken.DoesNotExist:
        raise ValueError("Invalid refresh token")

    if stored.is_expired():
        stored.revoked = True
        stored.save(update_fields=["revoked"])
        raise ValueError("Refresh token expired")

    user = stored.user

    # Revoke old token
    stored.revoked = True
    stored.save(update_fields=["revoked"])

    # Issue new opaque token
    new_plain = create_refresh_token_for_user(user, request=request)

    # Create new JWT access token (lifetime comes from SIMPLE_JWT)
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)

    return user, access, new_plain


# ------------------------------------------------------------
# 🔹 Create JWT + opaque refresh token pair
# ------------------------------------------------------------
def get_tokens_for_user(user, request=None, remember_me=False):
    """
    Creates:
      ✔ JWT Access Token   → SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
      ✔ JWT Refresh Token  → SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
      ✔ Opaque Refresh Token (DB stored)
    """

    refresh = RefreshToken.for_user(user)

    # 🔥 REMOVE ALL manual expiry overrides
    # SIMPLE_JWT handles expiry automatically

    # Custom claims
    refresh["role"] = user.role.name if user.role else None
    refresh["phone_number"] = user.phone_number
    refresh["full_name"] = user.full_name
    refresh["is_superuser"] = user.is_superuser
    refresh["iss"] = "django_issuer"

    if user.role:
        permissions = list(user.role.permissions.values_list("codename", flat=True))
    else:
        permissions = []

    refresh["permissions"] = permissions

    # Mirror custom claims into access token
    access_token = refresh.access_token
    access_token["role"] = refresh["role"]
    access_token["permissions"] = permissions
    access_token["iss"] = "django_issuer"

    # Generate opaque refresh token stored in DB
    opaque_token_plain = create_refresh_token_for_user(
        user, request=request, remember_me=remember_me
    )

    return {
        "access": str(access_token),
        "refresh": str(refresh),
        "opaque_refresh_token": opaque_token_plain,
        "remember_me": remember_me,
    }


# ------------------------------------------------------------
# 🔹 Cleanup expired or revoked tokens
# ------------------------------------------------------------
def cleanup_expired_refresh_tokens():
    now = timezone.now()
    StoredRefreshToken.objects.filter(revoked=True).delete()
    StoredRefreshToken.objects.filter(expires_at__lt=now).delete()
