from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PetTypeViewSet, PetBreedViewSet

router = DefaultRouter()
router.register(r'pet-types', PetTypeViewSet)
router.register(r'pet-breeds', PetBreedViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
