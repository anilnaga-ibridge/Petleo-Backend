from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import PetOwnerProfile
from .serializers import PetOwnerProfileSerializer

from .models import PetOwnerProfile, PetOwnerAddress, FavoriteProvider
from .serializers import PetOwnerProfileSerializer, PetOwnerAddressSerializer, FavoriteProviderSerializer

class PetOwnerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = PetOwnerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # request.user is already a PetOwnerProfile instance
        return PetOwnerProfile.objects.filter(id=self.request.user.id)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PetOwnerAddressViewSet(viewsets.ModelViewSet):
    serializer_class = PetOwnerAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PetOwnerAddress.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FavoriteProviderViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteProviderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteProvider.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
