from rest_framework import viewsets, generics, permissions
from rest_framework.permissions import AllowAny
from admin_core.permissions import IsSuperAdmin

from .models import ProviderFieldDefinition, ProviderDocumentDefinition
from .serializers import (
    ProviderFieldDefinitionSerializer,
    ProviderDocumentDefinitionSerializer
)


# ---------------------------
# FIELD DEFINITIONS (PROFILE)
# ---------------------------
class ProviderFieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ProviderFieldDefinition.objects.all()
    serializer_class = ProviderFieldDefinitionSerializer
    # Default permission for write operations
    permission_classes = [IsSuperAdmin]

    def get_permissions(self):
        """
        Allow IsAuthenticated for list (GET), but require IsSuperAdmin for everything else.
        """
        if self.action == 'list':
            return [permissions.IsAuthenticated()]
        return [IsSuperAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        target = self.request.query_params.get("target")
        if target:
            qs = qs.filter(target=target)
        return qs


class PublicProviderFieldDefinitionView(generics.ListAPIView):
    serializer_class = ProviderFieldDefinitionSerializer
    authentication_classes = []  # No authentication
    permission_classes = [AllowAny]

    def get_queryset(self):
        target = self.request.query_params.get("target")
        qs = ProviderFieldDefinition.objects.all()
        if target:
            qs = qs.filter(target=target)
        return qs.order_by("order")


# ---------------------------
# DOCUMENT DEFINITIONS
# ---------------------------
class ProviderDocumentDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ProviderDocumentDefinition.objects.all()
    serializer_class = ProviderDocumentDefinitionSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        target = self.request.query_params.get("target")
        if target:
            qs = qs.filter(target=target)
        return qs


class PublicProviderDocumentDefinitionView(generics.ListAPIView):
    serializer_class = ProviderDocumentDefinitionSerializer
    authentication_classes = []  # Public
    permission_classes = [AllowAny]

    def get_queryset(self):
        target = self.request.query_params.get("target")
        qs = ProviderDocumentDefinition.objects.all()
        if target:
            qs = qs.filter(target=target)
        return qs.order_by("order")
