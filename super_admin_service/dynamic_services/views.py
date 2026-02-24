from rest_framework import viewsets, permissions
from .models import Service, Capability
from .serializers import ServiceSerializer, CapabilitySerializer
from rest_framework.permissions import IsAuthenticated

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    # permission_classes = [IsAuthenticated]  <-- Removed logic here to use get_permissions

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        # ✅ Get Authorization Token (Debug only)
        auth_header = request.headers.get("Authorization")
        if auth_header:
             print("🔐 TOKEN RECEIVED:", auth_header[:20] + "...") 
        
        return super().list(request, *args, **kwargs)
class CapabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Capability.objects.all()
    serializer_class = CapabilitySerializer
    permission_classes = [IsAuthenticated]
