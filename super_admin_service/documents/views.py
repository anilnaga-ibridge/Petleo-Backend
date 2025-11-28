from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DocumentDefinition
from .serializers import DocumentDefinitionSerializer

# Use proper permissions for your project. Example: IsAdminUser for superadmin.
from rest_framework.permissions import IsAuthenticated, IsAdminUser

class DocumentDefinitionViewSet(viewsets.ModelViewSet):
    queryset = DocumentDefinition.objects.all().order_by("role", "code")
    serializer_class = DocumentDefinitionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]  # change as per your auth
    filter_backends = [filters.SearchFilter]
    search_fields = ["code", "label", "role"]

    # GET /api/definitions/?role=organization
    def list(self, request, *args, **kwargs):
        role = request.query_params.get("role")
        qs = self.get_queryset()
        if role:
            # include "both" entries
            qs = qs.filter(models.Q(role=role) | models.Q(role="both"))
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
