from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsSuperAdmin(BasePermission):
    """Allow access only to SuperAdmins."""
    def has_permission(self, request, view):
        user = request.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_super_admin", False):
            return True
        raise PermissionDenied("Only SuperAdmins can perform this action.")

class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not getattr(user, "is_authenticated", False):
            return False

        if getattr(user, "role", "").lower() in ["superadmin", "admin"]:
            return True

        return False