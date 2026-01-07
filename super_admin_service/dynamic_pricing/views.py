from rest_framework import viewsets, filters
from .models import PricingRule
from .serializers import PricingRuleSerializer

from rest_framework.permissions import IsAuthenticated
from admin_core.permissions import HasServicePermission

class PricingRuleViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD for Pricing Rules dynamically per Service, Category, and Facility.
    """
    queryset = PricingRule.objects.all().order_by("id")
    serializer_class = PricingRuleSerializer
    permission_classes = [IsAuthenticated, HasServicePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["service__display_name", "category__name", "facility__name"]
    ordering_fields = ["base_price", "created_at", "updated_at"]

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
