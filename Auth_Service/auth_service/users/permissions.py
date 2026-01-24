from rest_framework.permissions import BasePermission

class HasPermission(BasePermission):
    required_permission = None

    def has_permission(self, request, view):
        user_perms = request.auth.get('permissions', [])
        return self.required_permission in user_perms


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
