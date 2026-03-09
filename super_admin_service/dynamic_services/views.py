from rest_framework import viewsets, permissions, filters
from .models import Service, Capability
from .serializers import ServiceSerializer, CapabilitySerializer
from rest_framework.permissions import IsAuthenticated

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if auth_header:
             print("🔐 TOKEN RECEIVED:", auth_header[:20] + "...")
        return super().list(request, *args, **kwargs)


class CapabilityViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Capability keys.
    Super admins can create, edit, and delete capabilities from the UI.
    No code or terminal needed.
    """
    queryset = Capability.objects.all().order_by('service', 'group', 'key')
    serializer_class = CapabilitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['key', 'label', 'description', 'service', 'group']
    ordering_fields = ['key', 'service', 'group']
