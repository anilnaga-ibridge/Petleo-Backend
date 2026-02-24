from django.urls import path
from .views import (
    ServiceProviderProfileView,
    ServiceProviderDetailView,
    get_my_permissions,
    get_allowed_services,
    get_provider_role_templates,
    get_my_access,
    resolve_role_capabilities,
    get_dashboard_summary,
    PublicProviderViewSet,
    RatingSubmitView,
    PublicProviderRatingView,
    PublicProviderRatingView,
    resolve_booking_details,
)
from .views_profile import (
    ProviderProfileViewSet, 
    ProviderServiceViewSet, 
    ProviderServiceImageViewSet,
    ProviderCertificationViewSet, 
    ProviderGalleryViewSet, 
    ProviderPolicyViewSet,
    PublicProviderProfileView
)

urlpatterns = [
    path("profile/", ServiceProviderProfileView.as_view(), name="provider_profile"),
    path("profile/<str:auth_user_id>/", ServiceProviderDetailView.as_view(), name="provider_profile_detail"),
    path("permissions/", get_my_permissions, name="provider_permissions"),
    path("permissions/my-access/", get_my_access, name="provider_my_access"),
    path("allowed-services/", get_allowed_services, name="provider_allowed_services"),
    path("role-templates/", get_provider_role_templates, name="role_templates"),
    path("roles/resolve/", resolve_role_capabilities, name="resolve_role"),
    path("dashboard-summary/", get_dashboard_summary, name="dashboard_summary"),
    path("providers/active/", PublicProviderViewSet.as_view({'get': 'active'}), name="active_providers"),
    path("rating/", RatingSubmitView.as_view(), name="submit_rating"),
    path('resolve-details/', resolve_booking_details, name='resolve_details'),
    path("public-ratings/<uuid:provider_id>/", PublicProviderRatingView.as_view(), name="public_ratings"),
    path("public-profile/<uuid:provider_id>/", PublicProviderProfileView.as_view(), name="public_provider_profile"),
]

from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, EmployeeAssignmentViewSet, CapabilityViewSet, ProviderRoleViewSet, ConsultationTypeViewSet
from .views_availability import AvailabilityViewSet, ScheduleViewSet, LeaveViewSet, BlockTimeViewSet

router = DefaultRouter()
router.register(r'public-providers', PublicProviderViewSet, basename='public-providers')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'employee-assignments', EmployeeAssignmentViewSet, basename='employee-assignments')
router.register(r'capabilities', CapabilityViewSet, basename='capabilities')
router.register(r'roles', ProviderRoleViewSet, basename='roles')
router.register(r'consultation-types', ConsultationTypeViewSet, basename='consultation-types')
router.register(r'availability', AvailabilityViewSet, basename='availability')
router.register(r'schedules', ScheduleViewSet, basename='schedules')
router.register(r'leaves', LeaveViewSet, basename='leaves')
router.register(r'block-times', BlockTimeViewSet, basename='block-times')

# Provider Profile Management
router.register(r'my-profile-detailed', ProviderProfileViewSet, basename='my-profile-detailed')
router.register(r'my-services', ProviderServiceViewSet, basename='my-services')
router.register(r'my-service-images', ProviderServiceImageViewSet, basename='my-service-images')
router.register(r'my-certifications', ProviderCertificationViewSet, basename='my-certifications')
router.register(r'my-gallery', ProviderGalleryViewSet, basename='my-gallery')
router.register(r'my-policies', ProviderPolicyViewSet, basename='my-policies')

urlpatterns += router.urls
