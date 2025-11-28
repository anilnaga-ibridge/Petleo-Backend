# from django.urls import path
# from .views import ProviderDynamicFieldsView, ProviderFieldSubmitView

# urlpatterns = [
#     path("definitions/", ProviderDynamicFieldsView.as_view()),
#     path("submit/", ProviderFieldSubmitView.as_view()),
# ]



from django.urls import path
from .views import (
    ProviderDynamicFieldsView,
    ProviderFieldSubmitView,
    ProviderFieldValuesListView,
    ProviderFieldValueDetailView,
    ProviderFieldValueUpdateView,
    ProviderFieldValueDeleteView
)

urlpatterns = [
    path("definitions/", ProviderDynamicFieldsView.as_view()),
    path("submit/", ProviderFieldSubmitView.as_view()),

    # CRUD
    path("values/", ProviderFieldValuesListView.as_view()),     # GET ALL
    path("value/<uuid:field_id>/", ProviderFieldValueDetailView.as_view()),  # GET ONE
    path("value/<uuid:field_id>/update/", ProviderFieldValueUpdateView.as_view()),  # UPDATE
    path("value/<uuid:field_id>/delete/", ProviderFieldValueDeleteView.as_view()),  # DELETE
]
