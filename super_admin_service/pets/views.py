from rest_framework import viewsets
from .models import PetType, PetBreed
from .serializers import PetTypeSerializer, PetBreedSerializer

class PetTypeViewSet(viewsets.ModelViewSet):
    queryset = PetType.objects.all().order_by('-created_at')
    serializer_class = PetTypeSerializer


class PetBreedViewSet(viewsets.ModelViewSet):
    queryset = PetBreed.objects.all().order_by('-created_at')
    serializer_class = PetBreedSerializer
