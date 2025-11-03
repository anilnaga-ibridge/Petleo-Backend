from rest_framework import viewsets, filters
from .models import Pricing
from .serializers import PricingSerializer

class PricingViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD for Pricing dynamically per Service, Category, and Facility.
    """
    queryset = Pricing.objects.all().order_by("id")
    serializer_class = PricingSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["service__display_name", "category__name", "facility__name"]
    ordering_fields = ["price", "created_at", "updated_at"]

    def get_queryset(self):
        """
        Filter by service, category, or facility via query params
        ?service=1&category=2&facility=5
        """
        queryset = super().get_queryset()
        params = self.request.query_params
        service_id = params.get("service")
        category_id = params.get("category")
        facility_id = params.get("facility")

        if service_id:
            queryset = queryset.filter(service_id=service_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if facility_id:
            queryset = queryset.filter(facility_id=facility_id)
        return queryset
