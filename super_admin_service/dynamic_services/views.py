from rest_framework import viewsets, permissions
from .models import Service, Capability
from .serializers import ServiceSerializer, CapabilitySerializer
from rest_framework.permissions import IsAuthenticated

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        # ✅ Get Authorization Token
        auth_header = request.headers.get("Authorization")
        print("🔐 TOKEN RECEIVED:", auth_header)  # prints in terminal / backend console
        # ✅ Optional: Extract only the actual token (remove "Bearer ")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        print("🔑 Actual Access Token:", token)
        return super().list(request, *args, **kwargs)
class CapabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Capability.objects.all()
    serializer_class = CapabilitySerializer
    permission_classes = [IsAuthenticated]
