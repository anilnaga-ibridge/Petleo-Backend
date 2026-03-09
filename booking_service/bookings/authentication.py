from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class BookingJWTAuthentication(JWTAuthentication):
    """
    Lightweight microservice authentication.
    Does NOT require a local PetOwnerProfile or User model.
    Creates a polymorphic 'StaffUser' or 'PetOwnerUser' on the fly from JWT.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user_id = validated_token.get("user_id")
            if not user_id:
                return None

            role = (validated_token.get("role") or "").lower()
            
            # Polymorphic user object for DRF
            class MicroserviceUser:
                def __init__(self, uid, role, token):
                    self.id = uid
                    self.auth_user_id = uid  # For compatibility
                    self.role = role
                    self.is_authenticated = True
                    self.token = token
                    self.email = token.get('email', '')
                    self.full_name = token.get('full_name') or token.get('name', 'User')

                def __str__(self):
                    return f"{self.role.capitalize()} {self.id}"

                @property
                def is_provider(self):
                    return self.role in ["provider", "organization", "individual", "service_provider", "employee"]

                @property
                def is_staff(self):
                    return self.is_provider

            return (MicroserviceUser(user_id, role, validated_token), validated_token)

        except Exception as e:
            raise AuthenticationFailed(f"Authentication error: {str(e)}")
