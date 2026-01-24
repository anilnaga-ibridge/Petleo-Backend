from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CapabilityViewSet

router = DefaultRouter()
router.register(r'dynamic-permissions/capabilities', CapabilityViewSet, basename='capabilities')

urlpatterns = [
    path('', include(router.urls)),
]
