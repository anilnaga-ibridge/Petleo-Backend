from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PetOwnerProfileViewSet, PetOwnerAddressViewSet, FavoriteProviderViewSet

router = DefaultRouter()
router.register(r'profile', PetOwnerProfileViewSet, basename='pet-owner-profile')
router.register(r'addresses', PetOwnerAddressViewSet, basename='pet-owner-address')
router.register(r'favorites', FavoriteProviderViewSet, basename='pet-owner-favorite')

urlpatterns = [
    path('', include(router.urls)),
]
