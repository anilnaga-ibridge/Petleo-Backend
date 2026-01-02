





import logging
import uuid
from datetime import timedelta, datetime

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status, permissions, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes

from .models import Permission, Role, User, OTP, StoredRefreshToken
from .serializers import (
    RoleSerializer,
    PermissionSerializer,
    RegisterSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    UserUpdateSerializer,
)
from .permissions import IsOwnerOrOrgAdmin
from .kafka_producer import publish_event
from .utils import (
    create_otp_session,
    get_otp_session,
    increment_session_attempts,
    delete_otp_session,
    send_sms_via_provider,
    increment_rate_limit,
)
from .tokens import get_tokens_for_user, verify_and_rotate_refresh_token

from .utils import generate_reset_pin_token
from rest_framework.decorators import action

from .utils import verify_reset_pin_token


from .models import EmailTemplate
from .serializers import EmailTemplateSerializer, SendManualEmailSerializer
from .email_utils import send_automatic_registration_email_for_user
from django.shortcuts import get_object_or_404




logger = logging.getLogger(__name__)
User = get_user_model()

# Settings constants
OTP_TTL_MINUTES = int(getattr(settings, "OTP_TTL_SECONDS", 600)) // 60
RATE_LIMIT_WINDOW = getattr(settings, "OTP_RATE_LIMIT_WINDOW_SECONDS", 3600)
RATE_LIMIT_MAX = getattr(settings, "OTP_RATE_LIMIT_MAX_PER_WINDOW", 5)
STATIC_SUPERADMIN_PHONE = getattr(settings, "STATIC_SUPERADMIN_PHONE", None)
STATIC_SUPERADMIN_OTP = getattr(settings, "STATIC_SUPERADMIN_OTP", None)

RESET_TOKEN_TTL_SECONDS = 10 * 60  # 10 minutes (tweak as needed)
RESET_TOKEN_CACHE_PREFIX = "reset_token:"

# ---------------------
# Helper: calendar-day comparison (server local timezone)
# ---------------------
def is_pin_valid_today(user):
    """
    Return True if the user's PIN is valid (not expired).
    """
    if not user.pin_expires_at:
        return False
    
    return timezone.now() < user.pin_expires_at


# ---------------------- REGISTER ----------------------
#         return Response(response, status=status.HTTP_201_CREATED)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.debug("🔵 REGISTER REQUEST DATA: %s", request.data)
        logger.debug("🔵 REGISTER HEADERS: %s", request.headers)

        # ---------------------------------------------------------------
        # 1. Security Check for Employee Registration
        # ---------------------------------------------------------------
        # ---------------------------------------------------------------
        # 1. Security Check for Employee Registration
        # ---------------------------------------------------------------
        role_input = request.data.get('role', '')
        
        # Resolve Role ID to Name if necessary
        role_name = str(role_input).lower()
        try:
            # If input is an ID (int or digit string), fetch the role name
            if isinstance(role_input, int) or (isinstance(role_input, str) and role_input.isdigit()):
                role_obj = Role.objects.get(id=int(role_input))
                role_name = role_obj.name.lower()
            # If input is a name, ensure it exists (optional, but good for validation)
            else:
                 role_obj = Role.objects.filter(name__iexact=role_input).first()
                 if role_obj:
                     role_name = role_obj.name.lower()
        except Role.DoesNotExist:
            pass # Let serializer handle invalid role error later

        employee_roles = ["employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "lab tech", "pharmacy", "vitalsstaff", "vitals staff"]
        
        if role_name in employee_roles:
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentication required to register an employee."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if logged-in user is an Organization
            # Note: request.user.role is a Role model instance
            user_role_name = request.user.role.name.lower() if request.user.role else ""
            if user_role_name != 'organization':
                return Response(
                    {"detail": "Only organizations can register employees."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set organization_id if employee
        user = serializer.save()
        if role_input in employee_roles:
            user.organization_id = request.user.id
            user.status = 'PENDING'
            user.save(update_fields=['organization_id', 'status'])
        
        phone = user.phone_number
        
        # --------------------
        # Send static/DB template email immediately (non-blocking to user flow)
        # --------------------
        # Send automatic registration email via Kafka
        try:
            email_payload = {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.name.lower() if user.role else "user"
            }
            publish_event("SEND_EMAIL", email_payload)
            logger.info(f"Published SEND_EMAIL event for user {user.id}")
        except Exception:
            logger.exception("Failed to publish SEND_EMAIL event")

        # Continue with OTP / rate-limit and event publishing logic
        

        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response({"detail": "Too many OTP requests for this phone."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        session_id, otp = create_otp_session(phone, purpose="register")
        message = f"Your registration OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
        sms_ok = send_sms_via_provider(phone, message)

        # Kafka Event — send user role name
        try:
            user_role_name = user.role.name.lower() if getattr(user, "role", None) else None
            payload = {
                "auth_user_id": str(user.id),
                "phone_number": phone,
                "email": user.email,
                "full_name": user.full_name,
                "role": user_role_name,
            }

            # If Employee (or similar role), attach Organization ID (from logged-in user)
            employee_roles = ["employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "lab tech", "pharmacy", "vitalsstaff", "vitals staff"]
            if user_role_name in employee_roles:
                payload['organization_id'] = str(request.user.id)
                payload['created_by'] = str(request.user.id)

            publish_event("USER_CREATED", payload)
        except Exception:
            logger.exception("Kafka USER_CREATED publish failed")

        response = {
            "message": "User registered. OTP sent for verification.",
            "session_id": session_id,
            "sms_sent": sms_ok,
        }

        if getattr(settings, "SMS_BACKEND", "console") == "console":
            response["otp"] = otp

        return Response(response, status=status.HTTP_201_CREATED)

# ----------------------
# Send OTP (keeps your auto_verify_login behavior)
# ----------------------
class SendOTPView(APIView):
    """Request OTP for login or registration (returns session_id)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone_number"]
        purpose = serializer.validated_data.get("purpose", "login")

        # Superadmin static OTP (dev)
        if STATIC_SUPERADMIN_PHONE and phone == STATIC_SUPERADMIN_PHONE and purpose == "login":
            return Response(
                {
                    "message": "Static OTP for super admin (dev mode).",
                    "session_id": "static-superadmin-session",
                    "sms_sent": True,
                    "otp": STATIC_SUPERADMIN_OTP,
                },
                status=status.HTTP_200_OK,
            )

        # If login attempt and user exists but not active → route to auto_verify_login
        if purpose == "login":
            try:
                user = User.objects.get(phone_number=phone)
                if not user.is_active:
                    purpose = "auto_verify_login"
            except User.DoesNotExist:
                return Response(
                    {"detail": "Phone number not registered. Please register first."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Rate limit using your util (may raise redis errors if redis is down)
        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response(
                {"detail": "Too many OTP requests. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Create OTP session
        session_id, otp = create_otp_session(phone, purpose=purpose)
        message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
        sms_ok = send_sms_via_provider(phone, message)

        response = {"message": "OTP sent successfully.", "session_id": session_id, "sms_sent": sms_ok}
        if getattr(settings, "SMS_BACKEND", "console") == "console":
            response["otp"] = otp

        return Response(response, status=status.HTTP_200_OK)


# ----------------------
# Verify OTP + handlers
# ----------------------
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]
        provided_otp = serializer.validated_data["otp"]
        remember_me = request.data.get("remember_me", False)

        # Fetch OTP session
        session = get_otp_session(session_id)
        if not session:
            return Response({"detail": "Invalid or expired session."},
                            status=status.HTTP_400_BAD_REQUEST)

        phone = session["phone_number"]
        purpose = session["purpose"]
        attempts = session.get("attempts", 0)

        # Limit OTP attempts
        if attempts >= 5:
            delete_otp_session(session_id)
            return Response({"detail": "Too many attempts."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Wrong OTP
        if session["otp"] != provided_otp:
            increment_session_attempts(session_id)
            return Response({"detail": "Invalid OTP."},
                            status=status.HTTP_400_BAD_REQUEST)

        # OTP correct → remove session
        delete_otp_session(session_id)

        # ===============================
        # 1️⃣ RESET PIN FLOW (UPDATED)
        # ===============================
        if purpose == "reset_pin":
            reset_token = generate_reset_pin_token(phone)
            return Response(
                {
                    "message": "OTP verified. You can now reset your PIN.",
                    "reset_pin": True,
                    "reset_token": reset_token,
                    "phone_number": phone,
                },
                status=status.HTTP_200_OK,
            )

        # ===============================
        # 2️⃣ REGISTRATION FLOW
        # ===============================
        if purpose == "register":
            return self.handle_registration_verify(phone)

        # ===============================
        # 3️⃣ NORMAL LOGIN FLOW
        # ===============================
        if purpose == "login":
            return self.handle_login(phone, request, remember_me)

        # ===============================
        # 4️⃣ AUTO VERIFY LOGIN FLOW
        # ===============================
        if purpose == "auto_verify_login":
            return self.handle_auto_verify_login(phone, request, remember_me)

        return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)

    # ==========================================================
    # EXISTING HANDLER METHODS (UPDATED TIMEZONE-SAFE)
    # ==========================================================

    def handle_registration_verify(self, phone):
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = True
        user.status = 'ACTIVE'
        if hasattr(user, "is_verified"):
            user.is_verified = True
        user.save(
            update_fields=["is_active", "is_verified", "status"]
            if hasattr(user, "is_verified")
            else ["is_active", "status"]
        )

        # Kafka event
        try:
            user_data = {
                "auth_user_id": str(user.id),
                "phone_number": user.phone_number,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.name if user.role else None,
                "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
            }
            publish_event("USER_VERIFIED", user_data)
        except Exception as e:
            logger.error(f"Kafka USER_VERIFIED failed: {e}")

        return Response({"message": "Phone verified. You can now login."}, status=status.HTTP_200_OK)

    def handle_login(self, phone, request, remember_me):
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

        # Save last OTP login with correct local timezone
        tz = timezone.get_current_timezone()
        user.last_otp_login = timezone.now().astimezone(tz)
        user.save(update_fields=["last_otp_login"])

        tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

        require_set_pin = not is_pin_valid_today(user)

        res = transform_for_frontend(tokens, user, require_set_pin=require_set_pin)
        res["message"] = "OTP verified. Login successful."
        res["remember_me"] = remember_me
        return Response(res, status=status.HTTP_200_OK)

    def handle_auto_verify_login(self, phone, request, remember_me):
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

        if not user.is_active:
            user.is_active = True
            if hasattr(user, "is_verified"):
                user.is_verified = True
            user.save(
                update_fields=["is_active", "is_verified"]
                if hasattr(user, "is_verified")
                else ["is_active"]
            )

            try:
                user_data = {
                    "auth_user_id": str(user.id),
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.name if user.role else None,
                }
                publish_event("USER_VERIFIED", user_data)
            except Exception as e:
                logger.error(f"Kafka USER_VERIFIED failed: {e}")

        # Save last OTP login with correct timezone
        tz = timezone.get_current_timezone()
        user.last_otp_login = timezone.now().astimezone(tz)
        user.save(update_fields=["last_otp_login"])

        tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

        require_set_pin = not is_pin_valid_today(user)

        res = transform_for_frontend(tokens, user, require_set_pin=require_set_pin)
        res["message"] = "OTP verified. Account verified and logged in."
        res["remember_me"] = remember_me
        return Response(res, status=status.HTTP_200_OK)


# ---------------------- SET PIN ----------------------
class SetPinView(APIView):
    """
    Allows PIN set if:
    - User is authenticated (normal SET PIN)
    - OR reset_token is provided (RESET PIN after OTP)
    """

    permission_classes = [AllowAny]  # We manually validate

    def post(self, request):
        pin = request.data.get("pin")
        if not pin or not pin.isdigit() or len(pin) not in (4, 6):
            return Response({"detail": "PIN must be 4 or 6 digits."},
                            status=status.HTTP_400_BAD_REQUEST)

        reset_token = request.headers.get("X-Reset-Token")
        tz = timezone.get_current_timezone()

        # =======================================
        # Case 1: RESET PIN using reset_token
        # =======================================
        if reset_token:
            payload = verify_reset_pin_token(reset_token)
            if not payload:
                return Response({"detail": "Invalid or expired reset token."},
                                status=status.HTTP_400_BAD_REQUEST)

            phone = payload["phone_number"]
            try:
                user = User.objects.get(phone_number=phone)
            except User.DoesNotExist:
                return Response({"detail": "User not found."},
                                status=status.HTTP_404_NOT_FOUND)

        # =======================================
        # Case 2: CHANGE PIN (logged in user)
        # =======================================
        else:
            if not request.user.is_authenticated:
                return Response({"detail": "Authentication required."},
                                status=status.HTTP_401_UNAUTHORIZED)
            user = request.user

        # =======================================
        # Save new PIN
        # =======================================
        user.pin_hash = make_password(pin)
        now = timezone.now().astimezone(tz)
        user.pin_set_at = now
        
        # Set expiry to midnight of the current day
        tomorrow = now.date() + timedelta(days=1)
        midnight = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
        user.pin_expires_at = midnight

        user.last_pin_login = None
        user.save(update_fields=["pin_hash", "pin_set_at", "pin_expires_at", "last_pin_login"])

        return Response({"message": "PIN set successfully."}, status=status.HTTP_200_OK)





# class LoginWithPinView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         phone = request.data.get("phone_number")
#         pin = request.data.get("pin")
#         remember_me = request.data.get("remember_me", False)

#         if not phone or not pin:
#             return Response(
#                 {"detail": "phone_number and pin are required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             user = User.objects.get(phone_number=phone)
#         except User.DoesNotExist:
#             return Response(
#                 {"detail": "Phone not registered."},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         if not user.pin_hash:
#             return Response(
#                 {"detail": "No PIN set. Please login via OTP and set a PIN."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # ❌ REMOVED → PIN no longer expires daily
#         # if not is_pin_valid_today(user):
#         #     return Response(
#         #         {"detail": "PIN expired. Please login using OTP."},
#         #         status=status.HTTP_400_BAD_REQUEST
#         #     )

#         if not check_password(pin, user.pin_hash):
#             return Response(
#                 {"detail": "Invalid PIN."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # success -> update last_pin_login and issue tokens
#         user.last_pin_login = timezone.now().astimezone(timezone.get_current_timezone())
#         user.save(update_fields=["last_pin_login"])

#         tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)

#         res = transform_for_frontend(tokens, user, require_set_pin=False)
#         res["message"] = "PIN verified. Login successful."
#         res["remember_me"] = remember_me

#         return Response(res, status=status.HTTP_200_OK)
    
    
    
    
    
    
class LoginWithPinView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone_number")
        pin = request.data.get("pin")
        remember_me = request.data.get("remember_me", False)
        action = request.data.get("action", "login")  # login | reverify

        # 1. Determine User
        user = None
        if request.user.is_authenticated:
            user = request.user
        elif phone:
            try:
                user = User.objects.get(phone_number=phone)
            except User.DoesNotExist:
                return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)
        else:
             return Response({"detail": "Phone number required for login."}, status=status.HTTP_400_BAD_REQUEST)

        if not pin:
            return Response({"detail": "PIN is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.pin_hash:
            return Response(
                {"detail": "No PIN set. Please login via OTP and set a PIN."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check Expiry
        if not is_pin_valid_today(user):
             return Response(
                {"detail": "PIN expired. Please login via OTP.", "code": "PIN_EXPIRED"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate PIN
        if not check_password(pin, user.pin_hash):
            return Response({"detail": "Invalid PIN."}, status=status.HTTP_400_BAD_REQUEST)

        # Update last pin login time
        user.last_pin_login = timezone.now()
        user.save(update_fields=["last_pin_login"])

        # ====================================================
        # 1️⃣ REVERIFY MODE — only unlock, do NOT issue tokens
        # ====================================================
        if action == "reverify":
            return Response({
                "message": "PIN verified.",
                "require_set_pin": False,
                "is_reverify": True
            }, status=status.HTTP_200_OK)

        # ====================================================
        # 2️⃣ FULL LOGIN MODE — issue JWT tokens
        # ====================================================
        tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)
        res = transform_for_frontend(tokens, user, require_set_pin=False)
        res["message"] = "PIN verified. Login successful."
        res["remember_me"] = remember_me
        res["is_reverify"] = False

        return Response(res, status=status.HTTP_200_OK)

# ---------------------- CHANGE PIN ----------------------
class ChangePinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_pin = request.data.get("old_pin")
        new_pin = request.data.get("new_pin")
        confirm_pin = request.data.get("confirm_new_pin")

        # Validate fields
        if not old_pin or not new_pin or not confirm_pin:
            return Response(
                {"detail": "old_pin, new_pin and confirm_new_pin are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_pin != confirm_pin:
            return Response(
                {"detail": "New PINs do not match."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not new_pin.isdigit() or len(new_pin) not in (4, 6):
            return Response(
                {"detail": "New PIN must be 4 or 6 digits."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # Check old PIN
        if not user.pin_hash or not check_password(old_pin, user.pin_hash):
            return Response(
                {"detail": "Old PIN is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save new PIN
        user.pin_hash = make_password(new_pin)
        tz = timezone.get_current_timezone()
        now = timezone.now().astimezone(tz)
        user.pin_set_at = now
        
        # Set expiry to midnight
        tomorrow = now.date() + timedelta(days=1)
        midnight = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
        user.pin_expires_at = midnight

        user.last_pin_login = None
        user.save(update_fields=["pin_hash", "pin_set_at", "pin_expires_at", "last_pin_login"])

        return Response(
            {"message": "PIN changed successfully."},
            status=status.HTTP_200_OK
        )


# ---------------------- RESET PIN ----------------------
class ResetPinView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone_number")
        if not phone:
            return Response({"detail": "phone_number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

        # Rate limit
        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response({"detail": "Too many OTP requests."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Create OTP session
        session_id, otp = create_otp_session(phone, purpose="reset_pin")
        message = f"Your OTP to reset PIN is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
        sms_ok = send_sms_via_provider(phone, message)

        resp = {
            "message": "OTP sent for PIN reset.",
            "session_id": session_id,
            "sms_sent": sms_ok,
            "reset_pin": True,
        }

        # include OTP in console mode
        if getattr(settings, "SMS_BACKEND", "console") == "console":
            resp["otp"] = otp

        return Response(resp, status=status.HTTP_200_OK)


# ---------------------- REFRESH TOKEN ----------------------
# class RefreshTokenView(APIView):
#     """Accept opaque refresh token, rotate and return new access + refresh."""
#     permission_classes = [AllowAny]

#     def post(self, request):
#         token = request.data.get("refresh")
#         if not token:
#             return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             user, access, new_refresh = verify_and_rotate_refresh_token(token, request=request)
#         except ValueError as e:
#             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({"access": access, "refresh": new_refresh}, status=status.HTTP_200_OK)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user, access, new_refresh = verify_and_rotate_refresh_token(refresh_token)

            return Response({
                "access": access,
                "refresh": new_refresh,      # optional rotation
                "user_id": user.id
            })
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

# ---------------------- LOGOUT ----------------------
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_plain = request.data.get("refresh")

        # Revoke one refresh token
        if refresh_plain:
            from .tokens import _hash_token

            token_hash = _hash_token(refresh_plain)
            StoredRefreshToken.objects.filter(token_hash=token_hash).update(revoked=True)

        # Optionally revoke all
        if request.data.get("revoke_all"):
            StoredRefreshToken.objects.filter(user=request.user).update(revoked=True)

        # Increment token_version to invalidate JWTs
        request.user.token_version = (request.user.token_version or 0) + 1
        request.user.save(update_fields=["token_version"])

        return Response({"message": "Logged out. Tokens revoked."}, status=status.HTTP_200_OK)

from django.utils import timezone
from django.conf import settings
from datetime import timedelta

class CheckSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if not user.last_active_at:
            return Response({"require_pin": True})

        # If last active time older than timeout
        timeout = timedelta(minutes=settings.PIN_REVERIFY_TIMEOUT_MINUTES)
        if timezone.now() - user.last_active_at > timeout:
            return Response({"require_pin": True})

        return Response({"require_pin": False})
# ---------------------- REGISTER USER (ADMIN + SERVICE PROVIDER) ----------------------
@api_view(["POST"])
def register_superadmin(request):
    """
    Unified API to register:
      - Admin (created by SuperAdmin)
      - Service Provider (self-registration)
    """
    try:
        data = request.data
        email = data.get("email")
        phone = data.get("contact") or data.get("phone") or data.get("phone_number")
        contact = data.get("contact") or phone
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        user_type = data.get("user_type", "").lower()  # "admin" or "service_provider"
        provider_type = data.get("provider_type", "organization")  # org / individual

        if not email or not contact or not user_type:
            return Response(
                {"error": "Missing required fields: email, contact, or user_type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate user: use phone variable
        existing_user = User.objects.filter(phone_number=phone).first()
        if existing_user and not existing_user.is_active:
            # Resend OTP automatically
            session_id, otp = create_otp_session(phone, purpose="register")
            message = f"Your OTP is: {otp} (valid {OTP_TTL_MINUTES} minutes)"
            send_sms_via_provider(phone, message)
            return Response(
                {
                    "message": "User already exists but not verified. OTP resent.",
                    "session_id": session_id,
                    "otp": otp,  # only for dev
                },
                status=status.HTTP_200_OK,
            )

        # ---------------------- ADMIN REGISTRATION (BY SUPERADMIN) ----------------------
        if user_type == "admin":
            # Ensure only SuperAdmin can create Admins
            created_by = request.headers.get("Created-By")
            if not created_by:
                return Response(
                    {"error": "Missing 'Created-By' header (SuperAdmin ID required)."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            try:
                super_admin = User.objects.get(id=created_by, is_super_admin=True)
            except User.DoesNotExist:
                return Response(
                    {"error": "Only SuperAdmin can create Admin users."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Create Role
            role, _ = Role.objects.get_or_create(name="Admin")

            user = User.objects.create(
                id=uuid.uuid4(),
                email=email,
                contact=contact,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
                is_super_admin=False,
            )

            event_data = {
                "auth_user_id": str(user.id),
                "email": user.email,
                "contact": user.contact,
                "role": "admin",
                "created_by": str(super_admin.id),
            }

            try:
                publish_event("ADMIN_CREATED", event_data, role="admin")
                logger.info(f"✅ ADMIN_CREATED event published for {user.email}")
            except Exception as e:
                logger.error(f"❌ Kafka ADMIN_CREATED publish failed: {e}")

            return Response(
                {"message": "Admin created successfully", "user_id": str(user.id)},
                status=status.HTTP_201_CREATED,
            )

        # ---------------------- SERVICE PROVIDER REGISTRATION ----------------------
        elif user_type == "service_provider":
            role, _ = Role.objects.get_or_create(name="ServiceProvider")

            user = User.objects.create(
                id=uuid.uuid4(),
                email=email,
                contact=contact,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
            )

            event_data = {
                "auth_user_id": str(user.id),
                "email": user.email,
                "contact": user.contact,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "role": "organization" if provider_type == "organization" else "individual",
                "permissions": [],
            }

            try:
                publish_event("USER_CREATED", event_data, role=provider_type)
                logger.info(f"✅ USER_CREATED event published for {user.email}")
            except Exception as e:
                logger.error(f"❌ Kafka USER_CREATED publish failed: {e}")

            return Response(
                {"message": "Service Provider registered successfully", "user_id": str(user.id)},
                status=status.HTTP_201_CREATED,
            )

        else:
            return Response(
                {"error": "Invalid user_type. Use 'admin' or 'service_provider'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.exception("❌ Failed to register user.")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----------------------
# Role & Permission ViewSets
# ----------------------
class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all().order_by("codename")
    serializer_class = PermissionSerializer
    # permission_classes = [permissions.IsAuthenticated]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().prefetch_related("permissions")
    serializer_class = RoleSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def assign_permissions(self, request, pk=None):
        role = get_object_or_404(Role, pk=pk)
        permission_ids = request.data.get("permissions", [])
        role.permissions.set(permission_ids)
        role.save()
        return Response({"message": "Permissions updated successfully."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def public_roles(request):
    """
    Return only roles that can be selected during user registration
    (organization and individual).
    """
    allowed_roles = ["organization", "individual"]
    roles = Role.objects.filter(name__in=allowed_roles)
    serializer = RoleSerializer(roles, many=True)
    return Response(serializer.data)


# ----------------------
# User ViewSet (basic CRUD + events)
# ----------------------
class UserViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrOrgAdmin]

    def get_queryset(self):
        user = self.request.user
        
        # 1. Super Admin / Admin -> See ALL users
        if user.is_superuser or (user.role and user.role.name.lower() == 'admin'):
            return User.objects.all()

        user_role = user.role.name.lower() if user.role else ""
        
        # 2. Organization -> See themselves + their employees
        if user_role == 'organization':
            from django.db.models import Q
            return User.objects.filter(Q(id=user.id) | Q(organization_id=user.id))
        
        # 3. Others -> See only themselves
        return User.objects.filter(id=user.id)

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        self.check_object_permissions(request, user)
        serializer = UserUpdateSerializer(user)
        return Response(serializer.data)

    def list(self, request):
        status_param = request.query_params.get("status")
        qs = self.get_queryset()

        if status_param == "active":
            qs = qs.filter(is_active=True)
        elif status_param == "inactive":
            qs = qs.filter(is_active=False)

        serializer = UserUpdateSerializer(qs, many=True)
        return Response(serializer.data)


    def partial_update(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        self.check_object_permissions(request, user)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Refresh from DB to get latest role relation
        user.refresh_from_db()

        # Resolve dynamic role safely
        dynamic_role = (
            getattr(user.role, "name", None)
            or serializer.data.get("role")
            or request.data.get("role")
        )

        logger.info(f"🧩 Dynamic role resolved: {dynamic_role} for user {user.id}")

        if dynamic_role:
            publish_event(
                event_type="USER_UPDATED",
                data={
                    "auth_user_id": str(user.id),
                    "full_name": serializer.data.get("full_name") or user.full_name,
                    "email": serializer.data.get("email") or user.email,
                    "phone_number": serializer.data.get("phone_number") or user.phone_number,
                    "role": dynamic_role,
                },
            )
            logger.info(f"✅ USER_UPDATED event published for role '{dynamic_role}'")
        else:
            logger.warning("⚠️ Skipping USER_UPDATED event: no valid role found.")

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        return self.partial_update(request, pk)

    def destroy(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        self.check_object_permissions(request, user)
        user_id = str(user.id)

        dynamic_role = user.role.name if user.role else None

        if dynamic_role:
            publish_event(
                event_type="USER_DELETED",
                data={
                    "auth_user_id": user_id,
                    "role": dynamic_role,
                },
            )
            logger.info(f"✅ USER_DELETED event published for role '{dynamic_role}'")
        else:
            logger.warning("⚠️ Skipping USER_DELETED event: no valid role found.")

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id")
        phone_number = request.data.get("phone_number")
        purpose = request.data.get("purpose", "login")

        if not session_id and not phone_number:
            return Response({"detail": "session_id or phone_number is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 1. Try to get existing session
        session = None
        if session_id:
            session = get_otp_session(session_id)

        # 2. If session exists, use its data
        if session:
            phone = session["phone_number"]
            purpose = session["purpose"]
        
        # 3. If no session, but we have phone_number (Expired session case)
        elif phone_number:
            phone = phone_number
            # purpose is already set from request or default
        
        else:
            return Response({"detail": "Invalid or expired session."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Rate limit protection
        if not increment_rate_limit(phone, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX):
            return Response({"detail": "Too many OTP requests."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Create NEW OTP session (overwrite)
        new_session_id, new_otp = create_otp_session(phone, purpose=purpose)

        # Prepare message
        if purpose == "login":
            message = f"Your login OTP is: {new_otp} (valid {OTP_TTL_MINUTES} minutes)"
        elif purpose == "reset_pin":
            message = f"Your OTP to reset PIN is: {new_otp} (valid {OTP_TTL_MINUTES} minutes)"
        else:
            message = f"Your verification OTP is: {new_otp} (valid {OTP_TTL_MINUTES} minutes)"

        sms_ok = send_sms_via_provider(phone, message)

        resp = {
            "message": "OTP resent successfully.",
            "session_id": new_session_id,
            "sms_sent": sms_ok
        }

        if getattr(settings, "SMS_BACKEND", "console") == "console":
            resp["otp"] = new_otp

        return Response(resp, status=status.HTTP_200_OK)

# ----------------------
# Helper: transform_for_frontend
# ----------------------
def transform_for_frontend(tokens, user, require_set_pin=False):
    """Transform backend user and tokens into frontend-expected structure."""
    
    # Determine capabilities based on role
    capabilities = []
    if user.role:
        role_name = user.role.name.upper()
        if role_name in ['DOCTOR', 'RECEPTIONIST', 'VITALS_STAFF', 'LAB_TECH', 'PHARMACY']:
            capabilities.append('VETERINARY_MODULE')
        elif role_name == 'ORGANIZATION':
            capabilities.append('PROVIDER_MODULE')

    return {
        "userAbilityRules": [{"action": "manage", "subject": "all"}],
        "accessToken": tokens.get("access"),
        "refreshToken": tokens.get("refresh"),
        "auth_user_id": str(user.id),
        "userData": {
            "id": str(user.id),
            "auth_user_id": str(user.id),
            "fullName": user.full_name,
            "username": user.full_name,
            "avatar": "/images/avatars/avatar-1.png",
            "email": user.email or f"{user.phone_number}@demo.com",
            "role": user.role.name.upper() if user.role else None,
            "permissions": [p.codename for p in user.role.permissions.all()] if user.role else [],
            "phoneNumber": user.phone_number,
            "provider_id": str(user.organization_id) if user.organization_id else str(user.id),
            "capabilities": capabilities,
            "provider_type": (
                user.role.name 
                if (user.role and user.role.name in ["individual", "organization"]) 
                else None
            ),
        },
        "has_pin": bool(user.pin_hash),
        "pin_valid_today": is_pin_valid_today(user),
        "require_set_pin": require_set_pin,
    }

class UnifiedLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone_number")
        otp = request.data.get("otp")
        pin = request.data.get("pin")
        session_id = request.data.get("session_id")
        remember_me = request.data.get("remember_me", False)

        if not phone:
            return Response({"detail": "phone_number is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({"detail": "Phone not registered."}, status=status.HTTP_404_NOT_FOUND)

        if user.status == 'DISABLED' or not user.is_active:
            return Response({"detail": "Account is disabled or pending verification."}, status=status.HTTP_403_FORBIDDEN)

        # 1. Handle OTP Login
        if otp and session_id:
            session = get_otp_session(session_id)
            if not session or session["phone_number"] != phone or session["otp"] != otp:
                return Response({"detail": "Invalid OTP or session."}, status=status.HTTP_400_BAD_REQUEST)
            
            delete_otp_session(session_id)
            user.last_otp_login = timezone.now()
            user.save(update_fields=["last_otp_login"])

        # 2. Handle PIN Login
        elif pin:
            if not user.pin_hash:
                return Response({"detail": "No PIN set. Login via OTP first."}, status=status.HTTP_400_BAD_REQUEST)
            if not check_password(pin, user.pin_hash):
                return Response({"detail": "Invalid PIN."}, status=status.HTTP_400_BAD_REQUEST)
            
            user.last_pin_login = timezone.now()
            user.save(update_fields=["last_pin_login"])
        
        else:
            return Response({"detail": "OTP or PIN required."}, status=status.HTTP_400_BAD_REQUEST)

        # Success -> Issue tokens
        tokens = get_tokens_for_user(user, request=request, remember_me=remember_me)
        require_set_pin = not user.pin_hash
        res = transform_for_frontend(tokens, user, require_set_pin=require_set_pin)
        res["message"] = "Login successful."
        return Response(res, status=status.HTTP_200_OK)




# ----------------------------Mail Template ViewSet ----------------------------
class EmailTemplateViewSet(viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
  

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        template = self.get_object()

        if template.type != "automatic":
            return Response({"detail": "Only automatic templates can be default."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Clear defaults for same role
        EmailTemplate.objects.filter(
            role=template.role,
            type="automatic",
        ).update(is_default=False)

        template.is_default = True
        template.save()

        return Response({"message": "Default template updated successfully."})

    @action(detail=True, methods=["post"])
    def send_manual(self, request, pk=None):
        """
        Send manual email to a user using template.
        Accepts JSON: { "user_id": "<uuid>" } or used serializer below.
        """
        # Accept either { user_id } in body or use provided template id param
        serializer = SendManualEmailSerializer(data={"user_id": request.data.get("user_id"), "template_id": pk})
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        template_id = serializer.validated_data["template_id"]

        user = get_object_or_404(User, id=user_id)

        ok = send_manual_email_util(template_id, user)

        return Response({
            "sent": ok,
            "message": "Email sent successfully" if ok else "Email sending failed"
        })
class SendManualEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not getattr(request.user, "is_super_admin", False):
            return Response({"detail": "Only SuperAdmin allowed"}, status=403)

        serializer = SendManualEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        template_id = serializer.validated_data["template_id"]

        user = get_object_or_404(User, id=user_id)
        template = get_object_or_404(EmailTemplate, id=template_id, is_active=True)

        context = {
            "full_name": getattr(user, "full_name", ""),
            "email": user.email,
            "role": getattr(user.role, "name", None) or "",
            "user_id": str(user.id),
        }
        ok = send_email_from_template(template, user.email, context)
        if ok:
            return Response({"message": "Email sent successfully"}, status=200)
        return Response({"detail": "Failed to send email"}, status=500)
