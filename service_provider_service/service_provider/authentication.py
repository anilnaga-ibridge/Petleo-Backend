from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from service_provider.models import VerifiedUser, OrganizationEmployee


class TransientUser:
    """
    Mock user object for authenticated external users (like Pet Owners) 
    who don't have a record in the local VerifiedUser table.
    """
    def __init__(self, auth_user_id, role='customer', email=None, full_name=None):
        self.auth_user_id = auth_user_id
        self.role = role
        self.email = email
        self.full_name = full_name
        self.is_authenticated = True
        self.is_staff = False
        self.is_superuser = False
        self.phone_number = None

    @property
    def username(self):
        return self.email

    @property
    def id(self):
        return self.auth_user_id

    @property
    def pk(self):
        return self.auth_user_id

    def __str__(self):
        return f"TransientUser({self.auth_user_id})"


class VerifiedUserJWTAuthentication(JWTAuthentication):
    """
    Reads the correct claim: "user_id"
    Matches it with VerifiedUser.auth_user_id
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            from django.utils import timezone
            log_msg = f"[{timezone.now()}] Token received: {str(raw_token)[:20]}...\n"
            
            try:
                validated_token = self.get_validated_token(raw_token)
                log_msg += f"  - Token Validated. Payload: {validated_token.payload}\n"
            except Exception as v_err:
                log_msg += f"  - Token Validation Failed: {str(v_err)}\n"
                with open("debug_auth.log", "a") as f: f.write(log_msg)
                raise AuthenticationFailed(f"Invalid token: {str(v_err)}")

            user_id = validated_token.get("user_id")
            if not user_id:
                log_msg += f"  - No user_id in token payload\n"
                with open("debug_auth.log", "a") as f: f.write(log_msg)
                return None
                
            try:
                user = VerifiedUser.objects.get(auth_user_id=user_id)
                log_msg += f"  - User found in DB: {user.email}\n"
                
                try:
                    employee = OrganizationEmployee.objects.get(auth_user_id=user_id)
                    if employee.status == 'DISABLED':
                        log_msg += f"  - Employee is DISABLED\n"
                        with open("debug_auth.log", "a") as f: f.write(log_msg)
                        raise AuthenticationFailed("Your account has been disabled by your organization.", code="user_disabled")
                except OrganizationEmployee.DoesNotExist:
                    log_msg += f"  - Not an employee (or record missing)\n"

            except VerifiedUser.DoesNotExist:
                log_msg += f"  - User NOT in DB, returning TransientUser\n"
                role = validated_token.get("role", "customer")
                email = validated_token.get("email")
                full_name = validated_token.get("full_name")
                
                user = TransientUser(
                    auth_user_id=user_id,
                    role=role,
                    email=email,
                    full_name=full_name
                )
                with open("debug_auth.log", "a") as f: f.write(log_msg)
                return (user, validated_token)

            with open("debug_auth.log", "a") as f: f.write(log_msg)
            return (user, validated_token)

        except AuthenticationFailed as e:
            with open("debug_auth.log", "a") as f:
                f.write(f"  - Auth Failed (Caught): {str(e)}\n")
            raise e
        except Exception as e:
            with open("debug_auth.log", "a") as f:
                f.write(f"  - Unexpected Auth Error: {str(e)}\n")
            raise AuthenticationFailed(f"Authentication error: {str(e)}")
