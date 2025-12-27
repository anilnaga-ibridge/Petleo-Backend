from django.urls import path
from .views import (
    ServiceProviderProfileView,
    ServiceProviderDetailView,
    get_my_permissions,
    get_allowed_services,
)

urlpatterns = [
    path("profile/", ServiceProviderProfileView.as_view(), name="provider_profile"),
    path("profile/<str:auth_user_id>/", ServiceProviderDetailView.as_view(), name="provider_profile_detail"),
    path("permissions/", get_my_permissions, name="provider_permissions"),
    path("allowed-services/", get_allowed_services, name="provider_allowed_services"),
]

from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, EmployeeAssignmentViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'employee-assignments', EmployeeAssignmentViewSet, basename='employee-assignments')

urlpatterns += router.urls
