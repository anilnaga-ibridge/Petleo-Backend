# from rest_framework.routers import DefaultRouter
# from .views import (
#     ProviderFieldDefinitionViewSet,
#     ProviderFieldValueViewSet
# )

# router = DefaultRouter()
# router.register("definitions", ProviderFieldDefinitionViewSet, basename="definitions")
# router.register("values", ProviderFieldValueViewSet, basename="values")

# urlpatterns = router.urls
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProviderFieldDefinitionViewSet, PublicProviderFieldDefinitionView

router = DefaultRouter()
router.register("definitions", ProviderFieldDefinitionViewSet, basename="definitions")

urlpatterns = [
    # 🔥 PUBLIC MUST COME BEFORE ROUTER
    path("definitions/public/", PublicProviderFieldDefinitionView.as_view(), name="public-provider-definitions"),

    path("", include(router.urls)),
]
