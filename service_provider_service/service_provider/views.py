from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone


from .models import (
    ServiceProvider, 
    VerifiedUser,
)
from .serializers import (
    ServiceProviderSerializer, 
)






class ServiceProviderProfileView(APIView):
    """
    POST: Create or update the service provider profile, including personal info, avatar, and status.
    """

    def post(self, request):
        # Extract the auth_user_id from the request body
        auth_user_id = request.data.get('auth_user_id')
        
        # Check if auth_user_id is provided
        if not auth_user_id:
            return Response({"error": "auth_user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to fetch the VerifiedUser by auth_user_id
        try:
            verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "VerifiedUser not found for this auth_user_id"}, status=status.HTTP_404_NOT_FOUND)

        # Now, try to fetch the ServiceProvider related to this VerifiedUser
        provider, created = ServiceProvider.objects.get_or_create(verified_user=verified_user)

        # Proceed to update the profile data
        serializer = ServiceProviderSerializer(provider, data=request.data, partial=True)
        
        if serializer.is_valid():
            avatar_file = request.FILES.get('avatar')

            if avatar_file:
                provider.avatar = avatar_file
                provider.avatar_size = f"{round(avatar_file.size / 1024, 2)} KB"
                provider.save(update_fields=["avatar", "avatar_size"])

            serializer.save()

            return Response({
                "message": "Provider profile updated successfully",
                "data": ServiceProviderSerializer(provider).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ServiceProviderDetailView(APIView):
    """
    GET: Fetch service provider profile by auth_user_id.
    """
    permission_classes = [AllowAny]

    def get(self, request, auth_user_id):
        try:
            verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
            provider = ServiceProvider.objects.get(verified_user=verified_user)
            return Response(ServiceProviderSerializer(provider).data)
        except (VerifiedUser.DoesNotExist, ServiceProvider.DoesNotExist):
            return Response({"error": "Provider not found"}, status=status.HTTP_404_NOT_FOUND)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_permissions(request):
    """
    GET /api/provider/permissions/
    Returns merged permissions for logged-in provider.
    """
    # Get VerifiedUser from request.user (set by middleware)
    # Assuming request.user is the VerifiedUser object or has auth_user_id
    # The middleware sets request.user to VerifiedUser instance
    
    verified_user = request.user
    
    # If request.user is not VerifiedUser (e.g. standard Django user), handle it
    if not hasattr(verified_user, 'provider_permissions'):
         # Try to fetch VerifiedUser if request.user is just a token user object
         # But based on previous context, request.user IS VerifiedUser
         pass

    permissions = verified_user.provider_permissions.values_list('permission_code', flat=True)
    
    return Response({
        "permissions": list(permissions)
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_allowed_services(request):
    """
    GET /api/provider/allowed-services/
    Returns list of services the provider can access.
    """
    verified_user = request.user
    
    # Check if user has allowed_services relation
    if not hasattr(verified_user, 'allowed_services'):
        return Response([])

    services = verified_user.allowed_services.values('service_id', 'name', 'icon')
    
    return Response(list(services))
