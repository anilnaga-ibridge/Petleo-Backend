from django.urls import path
from .views import (
    ServiceProviderProfileView,
    ServiceProviderDetailView,
    get_my_permissions,
    get_allowed_services,
    get_provider_role_templates,
    get_my_access,
    resolve_role_capabilities,
)

urlpatterns = [
    path("profile/", ServiceProviderProfileView.as_view(), name="provider_profile"),
    path("profile/<str:auth_user_id>/", ServiceProviderDetailView.as_view(), name="provider_profile_detail"),
    path("permissions/", get_my_permissions, name="provider_permissions"),
    path("permissions/my-access/", get_my_access, name="provider_my_access"),
    path("allowed-services/", get_allowed_services, name="provider_allowed_services"),
    path("role-templates/", get_provider_role_templates, name="role_templates"),
    path("roles/resolve/", resolve_role_capabilities, name="resolve_role"),
]

from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, EmployeeAssignmentViewSet, CapabilityViewSet, ProviderRoleViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'employee-assignments', EmployeeAssignmentViewSet, basename='employee-assignments')
router.register(r'capabilities', CapabilityViewSet, basename='capabilities')
router.register(r'roles', ProviderRoleViewSet, basename='roles')

urlpatterns += router.urls
