from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from service_provider.models import VerifiedUser


class VerifiedUserJWTAuthentication(JWTAuthentication):
    """
    Reads the correct claim: "user_id"
    Matches it with VerifiedUser.auth_user_id
    """

    def get_user(self, validated_token):

        # ✔ Central Auth always gives CLAIM = "user_id"
        user_id = validated_token.get("user_id")

        if not user_id:
            raise InvalidToken("Token missing user_id")

        # ✔ Match with your DB column "auth_user_id"
        try:
            return VerifiedUser.objects.get(auth_user_id=user_id)
        except VerifiedUser.DoesNotExist:
            raise InvalidToken("User not found in VerifiedUser table")
