from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Capability

class CapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Capability
        fields = ['id', 'key', 'name', 'description', 'service_type', 'is_active']

class CapabilityViewSet(viewsets.ModelViewSet):
    """
    CRUD for Capabilities.
    """
    queryset = Capability.objects.all().order_by('name')
    serializer_class = CapabilitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = super().get_queryset()
        service_type = self.request.query_params.get('service_type')
        if service_type:
            qs = qs.filter(service_type=service_type)
        return qs
