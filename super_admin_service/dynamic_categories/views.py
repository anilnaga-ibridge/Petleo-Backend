from rest_framework import viewsets
from .models import Category
from .serializers import CategorySerializer

from rest_framework.permissions import IsAuthenticated
from admin_core.permissions import HasServicePermission

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, HasServicePermission]
