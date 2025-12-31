from rest_framework import permissions
from .models import Clinic

class HasVeterinaryAccess(permissions.BasePermission):
    """
    Allows access only if the provider's plan includes the VETERINARY_MODULE capability.
    """

    def has_permission(self, request, view):
        # 1. Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # 2. Get the provider_id/clinic_id from the user context
        # Assuming the Auth Service passes the provider_id in the JWT or user object
        # For now, we'll assume the request.user object has a 'provider_id' attribute 
        # or we fetch the Clinic based on the user.
        
        # In a real scenario, we might need to look up the Clinic associated with the request.user
        # For this Phase 1, let's assume we can resolve the Clinic.
        
        # If the view is detail-based, has_object_permission will be called.
        # If list-based, we need to know the context.
        
        return True

    def has_object_permission(self, request, view, obj):
        # Check if the object's clinic has the capability
        clinic = None
        if isinstance(obj, Clinic):
            clinic = obj
        elif hasattr(obj, 'clinic'):
            clinic = obj.clinic
        elif hasattr(obj, 'owner') and hasattr(obj.owner, 'clinic'):
            clinic = obj.owner.clinic
            
        if not clinic:
            return False
            
        # Check capability
        # The capability key might be 'VETERINARY_MODULE' or similar
        capabilities = clinic.capabilities or {}
        return capabilities.get('VETERINARY_MODULE', False)

from functools import wraps
from rest_framework.exceptions import PermissionDenied

def require_capability(capability):
    """
    Decorator to enforce strict capability checks on API views.
    Usage: @require_capability('VETERINARY_VITALS')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            # 1. Get User Permissions (from JWT or DB)
            # Assuming request.user.permissions is populated by Auth Middleware
            user_perms = getattr(request.user, 'permissions', [])
            
            # 2. Check Capability
            if capability not in user_perms:
                raise PermissionDenied(f"Missing required capability: {capability}")
            
            return func(view, request, *args, **kwargs)
        return wrapper
    return decorator
