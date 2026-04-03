from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import (
    ServiceProvider, ProviderProfile, ProviderService, ProviderServiceImage,
    ProviderCertification, ProviderGallery, ProviderPolicy
)
from .serializers import (
    ProviderProfileSerializer, ProviderServiceSerializer, ProviderServiceImageSerializer,
    ProviderCertificationSerializer, ProviderGallerySerializer, ProviderPolicySerializer,
    PublicProviderProfileSerializer
)

class IsProviderOwner(permissions.BasePermission):
    """
    Custom permission to only allow providers to edit their own data.
    """
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'provider_profile'):
            return False
            
        auth_provider = request.user.provider_profile
        
        # ServiceProvider check
        if isinstance(obj, ServiceProvider):
            return obj.id == auth_provider.id
        
        # Check if object has a 'provider' attribute
        provider = getattr(obj, 'provider', None)
        if provider:
            return provider.id == auth_provider.id
            
        # Check if object has a 'provider_service' attribute (for images)
        service = getattr(obj, 'provider_service', None)
        if service:
            return service.provider.id == auth_provider.id
            
        return False

class BaseProviderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsProviderOwner]

    def get_queryset(self):
        if not hasattr(self.request.user, 'provider_profile'):
            return self.queryset.none()
        
        provider = self.request.user.provider_profile
        
        if hasattr(self.model, 'provider'):
            return self.queryset.filter(provider=provider)
        if hasattr(self.model, 'provider_service'):
            return self.queryset.filter(provider_service__provider=provider)
        return self.queryset.none()

    def perform_create(self, serializer):
        provider = self.request.user.provider_profile
        if hasattr(self.model, 'provider'):
            serializer.save(provider=provider)
        else:
            serializer.save()

class ProviderProfileViewSet(BaseProviderViewSet):
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer
    model = ProviderProfile

    def list(self, request, *args, **kwargs):
        provider = request.user.provider_profile
        obj, created = ProviderProfile.objects.get_or_create(provider=provider)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

class ProviderServiceViewSet(BaseProviderViewSet):
    queryset = ProviderService.objects.all()
    serializer_class = ProviderServiceSerializer
    model = ProviderService

class ProviderServiceImageViewSet(BaseProviderViewSet):
    queryset = ProviderServiceImage.objects.all()
    serializer_class = ProviderServiceImageSerializer
    model = ProviderServiceImage

class ProviderCertificationViewSet(BaseProviderViewSet):
    queryset = ProviderCertification.objects.all()
    serializer_class = ProviderCertificationSerializer
    model = ProviderCertification

class ProviderGalleryViewSet(BaseProviderViewSet):
    queryset = ProviderGallery.objects.all()
    serializer_class = ProviderGallerySerializer
    model = ProviderGallery

class ProviderPolicyViewSet(BaseProviderViewSet):
    queryset = ProviderPolicy.objects.all()
    serializer_class = ProviderPolicySerializer
    model = ProviderPolicy

    def list(self, request, *args, **kwargs):
        provider = request.user.provider_profile
        obj, created = ProviderPolicy.objects.get_or_create(provider=provider)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

class PublicProviderProfileView(APIView):
    """
    GET: Fetch fully aggregated public profile data.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, provider_id):
        # 🛡️ SECURITY: Only allow viewing profiles that are Active, Verified, and Subscribed
        # Align with ProviderRepository.get_active_providers_for_marketplace()
        queryset = ServiceProvider.objects.filter(
            profile_status='active',
            is_fully_verified=True,
            verified_user__subscription__is_active=True
        ).exclude(
            verified_user__role__iexact='superadmin'
        )

        provider = get_object_or_404(queryset, id=provider_id)
        
        # Ensure defaults exist
        ProviderProfile.objects.get_or_create(provider=provider)
        ProviderPolicy.objects.get_or_create(provider=provider)
        
        serializer = PublicProviderProfileSerializer(provider, context={'request': request})
        return Response(serializer.data)
