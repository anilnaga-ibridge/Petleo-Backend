from rest_framework.permissions import BasePermission

class HasPermission(BasePermission):
    required_permission = None

    def has_permission(self, request, view):
        user_perms = request.auth.get('permissions', [])
        return self.required_permission in user_perms
