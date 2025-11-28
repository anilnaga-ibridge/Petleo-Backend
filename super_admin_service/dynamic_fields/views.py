

from rest_framework import viewsets, generics
from rest_framework.permissions import AllowAny
from admin_core.permissions import IsSuperAdmin
from .models import ProviderFieldDefinition
from .serializers import ProviderFieldDefinitionSerializer


# 🔒 SUPERADMIN-ONLY CRUD
class ProviderFieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ProviderFieldDefinition.objects.all()
    serializer_class = ProviderFieldDefinitionSerializer
    permission_classes = [IsSuperAdmin]   # protected

    def get_queryset(self):
        qs = super().get_queryset()
        target = self.request.query_params.get("target")
        if target:
            qs = qs.filter(target=target)
        return qs


# 🔓 PUBLIC — NO AUTH REQUIRED
class PublicProviderFieldDefinitionView(generics.ListAPIView):
    serializer_class = ProviderFieldDefinitionSerializer
    authentication_classes = []  # <--- DISABLE ALL AUTH
    permission_classes = [AllowAny]  # <--- MARK PUBLIC

    def get_queryset(self):
        target = self.request.query_params.get("target")
        qs = ProviderFieldDefinition.objects.all()
        if target:
            qs = qs.filter(target=target)
        return qs.order_by("order")
