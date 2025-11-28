from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProviderHomePageViewSet,
    provider_home,
    page_preview_url,
)

router = DefaultRouter()
router.register("pages", ProviderHomePageViewSet, basename="provider-home-pages")

urlpatterns = [
    # CRUD for SuperAdmin (list/create/update/delete)
    path("", include(router.urls)),

    # Provider public homepage (used by providers frontend)
    path("provider-home/", provider_home, name="provider-home"),

    # Preview URL for SuperAdmin builder (iframe)
    path("pages/<uuid:pk>/preview-url/", page_preview_url, name="homepage-preview-url"),
]
