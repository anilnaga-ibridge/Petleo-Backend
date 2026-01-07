from rest_framework import viewsets
from .models import Category
from .serializers import CategorySerializer

from rest_framework.permissions import IsAuthenticated
from admin_core.permissions import HasServicePermission

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, HasServicePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {"detail": "System categories cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)
