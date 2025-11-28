from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProviderViewSet, ProviderDocumentSubmissionViewSet

router = DefaultRouter()
router.register(r"providers", ProviderViewSet, basename="provider")
router.register(r"submissions", ProviderDocumentSubmissionViewSet, basename="submission")

urlpatterns = [
    path("api/", include(router.urls)),
]
