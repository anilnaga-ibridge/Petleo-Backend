from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    """
    Allows full access only to SuperAdmin users.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Check if user is a superuser (from Django's built-in field)
        # Also check for role = "SuperAdmin" for backward compatibility
        return (getattr(user, "is_superuser", False) or 
                getattr(user, "role", None) == "SuperAdmin")
