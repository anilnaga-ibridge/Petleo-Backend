from django.urls import path
from provider_dynamic_fields.views import (
    ProviderDynamicFieldsView,
    ProviderFieldSubmitView,
    ProviderFieldValuesListView,
    ProviderFieldValueDetailView,
    ProviderFieldValueUpdateView,
    ProviderFieldValueDeleteView,
)

from provider_dynamic_fields.views_documents import (
    ProviderDocumentDefinitionsView,
    ProviderDocumentUploadView,
    ProviderDocumentListView,
    ProviderDocumentDetailView,
)
from provider_dynamic_fields.views_combined import ProviderProfileView
urlpatterns = [
    # Dynamic Fields
    path("definitions/", ProviderDynamicFieldsView.as_view()),
    path("submit/", ProviderFieldSubmitView.as_view()),
    path("values/", ProviderFieldValuesListView.as_view()),
    path("value/<uuid:field_id>/", ProviderFieldValueDetailView.as_view()),
    path("value/<uuid:field_id>/update/", ProviderFieldValueUpdateView.as_view()),
    path("value/<uuid:field_id>/delete/", ProviderFieldValueDeleteView.as_view()),

    # Documents
    path("documents/definitions/", ProviderDocumentDefinitionsView.as_view()),
    path("documents/upload/", ProviderDocumentUploadView.as_view()),
    path("documents/", ProviderDocumentListView.as_view()),
    path("documents/<uuid:pk>/", ProviderDocumentDetailView.as_view()),
    
    
    #combined profile
    path("profile/", ProviderProfileView.as_view(), name="provider-profile"),
]
