from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import PetOwnerProfile

class CustomerJWTAuthentication(JWTAuthentication):
    """
    Reads the 'user_id' claim from JWT and matches it with PetOwnerProfile.auth_user_id.
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

            try:
                # Local "shadow" profile
                profile = PetOwnerProfile.objects.get(auth_user_id=user_id)
                return (profile, validated_token)
            except PetOwnerProfile.DoesNotExist:
                # Check role in token before auto-creating
                role = (validated_token.get("role") or "").lower()
                email = validated_token.get("email", "").lower()
                
                if role in ["petowner", "pet_owner", "pet owner", "customer"]:
                    # CRITICAL: Check if a profile already exists for this email to prevent duplicates
                    if email:
                        existing = PetOwnerProfile.objects.filter(email__iexact=email).first()
                        if existing:
                            # Link this auth_user_id to the existing profile
                            existing.auth_user_id = user_id
                            existing.save()
                            return (existing, validated_token)

                    # Auto-create if they have the right role
                    full_name = validated_token.get("full_name") or validated_token.get("name") or "Pet Owner"
                    profile = PetOwnerProfile.objects.create(
                        auth_user_id=user_id,
                        full_name=full_name,
                        email=email,
                        phone_number=validated_token.get("phone_number", "")
                    )
                    return (profile, validated_token)
                
                # Allow Providers & Employees to authenticate without a local profile
                if role.upper() in ["PROVIDER", "ORGANIZATION", "INDIVIDUAL", "SERVICE_PROVIDER", "EMPLOYEE"]:
                    # Create a simple user object that has is_authenticated=True and id=user_id
                    class StaffUser:
                        id = user_id
                        is_authenticated = True
                        is_provider = True
                        def __str__(self): return f"Staff {user_id}"
                    
                    return (StaffUser(), validated_token)

                # Strictly enforce Pet Owner role for others
                raise AuthenticationFailed("Pet Owner profile not found and user role is not Pet Owner/Provider. Access denied.", code="profile_not_found")

        except Exception as e:
            raise AuthenticationFailed(f"Authentication error: {str(e)}")
