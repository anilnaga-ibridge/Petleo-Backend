from rest_framework import viewsets, filters
from .models import Facility
from .serializers import FacilitySerializer

from rest_framework.permissions import IsAuthenticated
from admin_core.permissions import HasServicePermission

class FacilityViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD for Facilities dynamically linked to each Service.
    """
    queryset = Facility.objects.all().order_by("id")
    serializer_class = FacilitySerializer
    permission_classes = [IsAuthenticated, HasServicePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "service__display_name"]
    ordering_fields = ["created_at", "updated_at"]

    def get_queryset(self):
        """
        Allow filtering by service ID (?service=1)
        """
        queryset = super().get_queryset()
        service_id = self.request.query_params.get("service")
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        return queryset
