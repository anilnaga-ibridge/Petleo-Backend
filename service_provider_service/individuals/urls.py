from django.urls import path
from .views import IndividualProfileCreateView, IndividualProfileDetailView

urlpatterns = [
    path("profile/", IndividualProfileCreateView.as_view(), name="individual-profile-create"),
    path("profile/<uuid:auth_user_id>/", IndividualProfileDetailView.as_view(), name="individual-profile-detail"),
]
