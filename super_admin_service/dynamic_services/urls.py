from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, CapabilityViewSet

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("capabilities", CapabilityViewSet, basename="capability")

urlpatterns = [
    path("", include(router.urls)),
]
