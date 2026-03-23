
# admin_core/urls.py
from rest_framework.routers import DefaultRouter
from .views import (
    AdminProfileViewSet, VerifiedUserViewSet, PermissionViewSet, 
    SuperAdminViewSet, SuperAdminDashboardViewSet
)

router = DefaultRouter()
router.register(r"admins", AdminProfileViewSet, basename="admins")
router.register(r"verified-users", VerifiedUserViewSet, basename="verifiedusers")
router.register(r"permissions", PermissionViewSet, basename="permissions")
router.register(r"superadmins", SuperAdminViewSet, basename="superadmins")
router.register(r"dashboard", SuperAdminDashboardViewSet, basename="dashboard")

urlpatterns = router.urls
