from rest_framework import permissions
from plans_coupens.models import ProviderPlanCapability
from dynamic_services.models import Service

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to super admins.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'is_super_admin', False))

class HasServicePermission(permissions.BasePermission):
    """
    Custom permission to check if the provider has the required permission
    (view, create, edit, delete) for the specific service.
    """

    def has_permission(self, request, view):
        # 1. Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # 2. Super Admins bypass checks
        if getattr(request.user, 'is_super_admin', False):
            return True

        # 3. Determine required action
        method = request.method
        required_action = None
        if method in permissions.SAFE_METHODS: # GET, HEAD, OPTIONS
            required_action = 'can_view'
        elif method == 'POST':
            required_action = 'can_create'
        elif method in ['PUT', 'PATCH']:
            required_action = 'can_edit'
        elif method == 'DELETE':
            required_action = 'can_delete'
        else:
            return False

        # 4. Identify Service ID
        # It could be in query params (?service=...) or body (service: ...)
        service_id = request.query_params.get('service') or request.data.get('service')
        
        # If accessing a detail route (e.g. /categories/1/), we might need to fetch the object first
        # But has_permission runs before get_object. 
        # For detail actions, we usually rely on has_object_permission, but let's try to handle basic cases here.
        
        if not service_id:
            # If no service_id in request, we might be listing all. 
            # In that case, we might allow it but filter the queryset later.
            # For now, let's assume service_id is required for write operations.
            if method in permissions.SAFE_METHODS:
                return True # Allow list, filtering happens in queryset
            
            # For write operations, we need to know which service context we are in.
            # If it's a detail view, we can check the object's service in has_object_permission
            return True 

        # 5. Check ProviderPlanPermission
        # We need to find a permission record for this user and service.
        # Note: ProviderPlanPermission links to Auth User Model.
        
        has_perm = ProviderPlanPermission.objects.filter(
            user=request.user,
            service__id=service_id
        ).first()

        if not has_perm:
            return False

        return getattr(has_perm, required_action, False)

    def has_object_permission(self, request, view, obj):
        # 1. Super Admins bypass
        if getattr(request.user, 'is_super_admin', False):
            return True

        # 2. Determine required action
        method = request.method
        required_action = None
        if method in permissions.SAFE_METHODS:
            required_action = 'can_view'
        elif method == 'POST':
            required_action = 'can_create'
        elif method in ['PUT', 'PATCH']:
            required_action = 'can_edit'
        elif method == 'DELETE':
            required_action = 'can_delete'
        else:
            return False

        # 3. Get Service from Object
        # Assuming obj has a 'service' attribute (Category, Facility, Pricing all do)
        service = getattr(obj, 'service', None)
        if not service:
            return False # Should not happen if models are correct

        # 4. Check Permission
        has_perm = ProviderPlanPermission.objects.filter(
            user=request.user,
            service=service
        ).first()

        if not has_perm:
            return False

        return getattr(has_perm, required_action, False)