from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed
from service_provider.models import VerifiedUser


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
            validated_token = self.get_validated_token(raw_token)
            
            # Debug: Print token payload
            # print(f"DEBUG: Token Payload: {validated_token.payload}")
            
            user_id = validated_token.get("user_id")
            if not user_id:
                print("DEBUG: No user_id in token")
                return None
                
            # print(f"DEBUG: Auth User ID from Token: {user_id}")

            try:
                user = VerifiedUser.objects.get(auth_user_id=user_id)
                # print(f"DEBUG: Found VerifiedUser: {user.email}")
            except VerifiedUser.DoesNotExist:
                print(f"DEBUG: VerifiedUser not found for auth_user_id: {user_id}")
                raise AuthenticationFailed("User not found in Service Provider Service", code="user_not_found")

            # VerifiedUser does not have is_active field
            # if not user.is_active:
            #     print("DEBUG: User is inactive")
            #     raise AuthenticationFailed("User is inactive", code="user_inactive")

            return (user, validated_token)

        except AuthenticationFailed as e:
            print(f"DEBUG: Auth Failed: {e}")
            raise e
        except Exception as e:
            print(f"DEBUG: Unexpected Auth Error: {e}")
            raise AuthenticationFailed(f"Authentication error: {str(e)}")
