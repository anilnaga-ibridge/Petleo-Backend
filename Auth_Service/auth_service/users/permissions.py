from rest_framework.permissions import BasePermission

class HasGranularPermission(BasePermission):
    """
    Checks if user has a specific capability and action.
    Usage: permission_classes = [HasGranularPermission('veterinary.vitals', 'create')]
    """
    def __init__(self, capability, action='v'):
        self.capability = capability
        self.action = action # 'v', 'c', 'e', 'd'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # In simplejwt, extra claims are in request.auth (the decoded token)
        summary = request.auth.get('permissions_summary', {})
        cap_perms = summary.get(self.capability, {})
        
        return cap_perms.get(self.action, False)

class IsClinicAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
            
        summary = request.auth.get('permissions_summary', {})
        admin_perms = summary.get('admin.roles', {})
        return admin_perms.get('v', False) or admin_perms.get('c', False)


class IsOwnerOrOrgAdmin(BasePermission):
    """
    Custom permission to only allow owners of an object or organization admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow Super Admin
        if getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_super_admin', False):
            return True

        # Allow if user is updating themselves
        if obj == request.user:
            return True
        
        # Allow if user is an organization admin and obj is their employee
        user_role = request.user.role.name.lower() if request.user.role else ""
        if user_role == 'organization':
            # Check if the object (user) belongs to this organization
            return str(obj.organization_id) == str(request.user.id)
            
        return False
