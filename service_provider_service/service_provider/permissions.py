from rest_framework import permissions

class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access based on management capabilities.
    Eliminates role-string checks in favor of granular permissions.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_caps = getattr(request.user, 'resolved_capabilities', set())
        
        # Check for administrative "Core" or management capabilities
        ADMIN_CAPS = {
            "SYSTEM_ADMIN_CORE_VIEW", "SYSTEM_ADMIN_CORE_EDIT",
            "CLINIC_MANAGEMENT_VIEW", "CLINIC_MANAGEMENT_EDIT",
            "ROLE_MANAGEMENT_VIEW", "ROLE_MANAGEMENT_EDIT"
        }
        
        # If user has ANY of these, they are considered an admin for this view
        if any(cap in user_caps for cap in ADMIN_CAPS):
            return True
            
        # Optional: Specialized "Super Admin" check if needed for ultra-privileged actions
        # but for now, capabilities are the source of truth.
            
        return False


class HasGranularCapability(permissions.BasePermission):
    """
    Method-aware granular capability check.
    Maps HTTP methods to CRUD suffixes:
    - GET -> _VIEW
    - POST -> _CREATE
    - PUT/PATCH -> _EDIT
    - DELETE -> _DELETE
    """
    def __init__(self, base_key=None):
        self.base_key = base_key

    def _get_required_suffix(self, method):
        if method in permissions.SAFE_METHODS:
            return "_VIEW"
        if method == "POST":
            return "_CREATE"
        if method in ["PUT", "PATCH"]:
            return "_EDIT"
        if method == "DELETE":
            return "_DELETE"
        return "_VIEW"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user_caps = getattr(request.user, 'resolved_capabilities', set())
        
        # 1. If no base_key, just check for authentication/any capability
        if not self.base_key:
            return len(user_caps) > 0

        # 2. Determine required granular key
        suffix = self._get_required_suffix(request.method)
        required_key = f"{self.base_key}{suffix}"

        # 3. Check if user has the key
        if required_key in user_caps:
            return True
            
        # 4. Fallback for 'SYSTEM_ADMIN' or 'CLINIC_MANAGEMENT' owners
        if "SYSTEM_ADMIN_CORE_EDIT" in user_caps or "CLINIC_MANAGEMENT_EDIT" in user_caps:
            return True

        return False


def require_granular_capability(base_key):
    """
    Factory to create a dynamic HasGranularCapability permission class.
    Usage: permission_classes = [require_granular_capability('VETERINARY_VISITS')]
    """
    class DynamicHasGranularCapability(HasGranularCapability):
        def __init__(self):
            super().__init__(base_key)
    return DynamicHasGranularCapability


class HasCapability(permissions.BasePermission):
    """Legacy: Simple check for a specific key (exact match)."""
    def __init__(self, capability_key=None):
        self.capability_key = capability_key

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        user_caps = getattr(request.user, 'resolved_capabilities', set())
        if not self.capability_key:
            return len(user_caps) > 0
            
        return self.capability_key in user_caps

def require_capability(capability_key):
    """
    Legacy factory for simple capability checks.
    """
    class DynamicHasCapability(HasCapability):
        def __init__(self):
            super().__init__(capability_key)
    return DynamicHasCapability
