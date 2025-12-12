
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProviderFieldDefinitionViewSet,
    PublicProviderFieldDefinitionView,
    ProviderDocumentDefinitionViewSet,
    PublicProviderDocumentDefinitionView
)
from .views_verification import ProviderDocumentVerificationViewSet

router = DefaultRouter()

# -----------------------------
# ✔ DO NOT TOUCH PROFILE ROUTES
# -----------------------------
router.register("definitions", ProviderFieldDefinitionViewSet, basename="definitions")
router.register("verification/documents", ProviderDocumentVerificationViewSet, basename="verification-documents")

urlpatterns = [

    # -----------------------------
    # PUBLIC ENDPOINTS
    # -----------------------------
    path("definitions/public/",
         PublicProviderFieldDefinitionView.as_view(),
         name="public-provider-definitions"),

    path("definitions/documents/public/",
         PublicProviderDocumentDefinitionView.as_view(),
         name="public-document-definitions"),

    # -----------------------------
    # DOCUMENTS CRUD (MANUAL ROUTES)
    # -----------------------------
    path(
        "definitions/documents/",
        ProviderDocumentDefinitionViewSet.as_view({
            "get": "list",
            "post": "create",
        }),
        name="document-definition-list",
    ),

    path(
        "definitions/documents/<uuid:pk>/",
        ProviderDocumentDefinitionViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="document-definition-detail",
    ),

    # -----------------------------
    # PROFILE ROUTER
    # -----------------------------
    path("", include(router.urls)),
]
