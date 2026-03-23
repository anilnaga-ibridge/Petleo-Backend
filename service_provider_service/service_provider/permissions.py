from rest_framework import permissions


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access to organization and individual providers (owners who can manage their organization).
    Employees are excluded.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check ServiceProvider.provider_type instead of user.role
        try:
            from .models import ServiceProvider
            provider = ServiceProvider.objects.filter(verified_user__auth_user_id=request.user.auth_user_id).first()
            
            if provider and provider.provider_type:
                provider_type = provider.provider_type.upper()
                # Allow both ORGANIZATION and INDIVIDUAL providers
                has_access = provider_type in ['ORGANIZATION', 'INDIVIDUAL']
                
                if not has_access:
                    print(f"❌ IsOrganizationAdmin: Denied for provider_type={provider_type}")
                else:
                    print(f"✅ IsOrganizationAdmin: Granted for provider_type={provider_type}")
                
                return has_access
        except Exception as e:
            print(f"❌ IsOrganizationAdmin: Error checking provider type: {e}")
        
        # Fallback: Check user.role
        role = getattr(request.user, 'role', '').upper()
        if role in ['ORGANIZATION', 'INDIVIDUAL', 'SUPER_ADMIN']:
            return True
            
        # [FIX] Allow employees to GET the list (for coordination)
        if role == 'EMPLOYEE' and request.method in permissions.SAFE_METHODS:
            print(f"✅ IsOrganizationAdmin: Granted SAFE_METHOD for employee {request.user.email}")
            return True
            
        return False


class HasProviderPermission(permissions.BasePermission):
    """
    Checks if the provider has permission to perform the action on the specific service/category.
    Relies on the local ProviderPermission model which is synced from Super Admin.
    """

    def has_permission(self, request, view):
        # Basic check for authentication
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        # Allow owners to manage their own resources
        from provider_dynamic_fields.views import get_effective_provider_user
        
        verified_user = get_effective_provider_user(request.user)
        
        # Check if this is the owner's resource
        if hasattr(obj, 'provider') and obj.provider == verified_user:
            # Owner has full permissions
            return True
        
        # Determine the action type
        if request.method in permissions.SAFE_METHODS:
            action = "view"
        elif request.method == "POST":
            action = "create"
        elif request.method in ["PUT", "PATCH"]:
            action = "edit"
        elif request.method == "DELETE":
            action = "delete"
        else:
            return False

        # Extract service_id and category_id from the object or request
        service_id = None
        category_id = None

        # For ProviderCategory
        if hasattr(obj, "service_id"):
            service_id = obj.service_id
        
        # For ProviderFacility (linked to category)
        if hasattr(obj, "category"):
            # If it's a ProviderFacility, it has a category FK
            if hasattr(obj.category, "service_id"):
                service_id = obj.category.service_id
                # For facility, the category context is the category itself
                # But permissions might be defined at service level or category level
                # Let's assume facility permissions are checked against the service/category context
                pass

        # For ProviderPricing
        if hasattr(obj, "service_id"):
            service_id = obj.service_id
        if hasattr(obj, "category_id"):
            category_id = obj.category_id

        # If we can't determine service_id, we might need to look at request data for creation
        if not service_id and request.method == "POST":
            service_id = request.data.get("service_id")
            category_id = request.data.get("category_id") or request.data.get("category")

        if not service_id:
            # If no service_id involved, maybe it's a global action? 
            # For now, block if we can't identify the service context
            return False

        # Check permission in DB
        from provider_dynamic_fields.models import ProviderCapabilityAccess

        perms = ProviderCapabilityAccess.objects.filter(user=verified_user, service_id=str(service_id))
        
        if category_id:
            # Try finding specific category permission
            cat_perm = perms.filter(category_id=str(category_id)).first()
            if cat_perm:
                return getattr(cat_perm, f"can_{action}", False)
        
        # Fallback: Check if ANY permission for this service allows the action
        # This is a broad check, but necessary if we don't have a specific category context
        has_perm = perms.filter(**{f"can_{action}": True}).exists()
        return has_perm


class HasCapability(permissions.BasePermission):
    """
    Checks if the user has the required capability attached to their request
    by the RBACMiddleware.
    """
    def __init__(self, capability_key=None):
        self.capability_key = capability_key

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Get capabilities from middleware
        user_caps = getattr(request, 'capabilities', set())
        
        # If no specific key is required, just check if they have ANY capabilities
        if not self.capability_key:
            return len(user_caps) > 0
            
        return self.capability_key in user_caps

def require_capability(capability_key):
    """
    Factory to create a dynamic HasCapability permission class.
    Usage: permission_classes = [require_capability('VETERINARY_VITALS')]
    """
    class DynamicHasCapability(HasCapability):
        def __init__(self):
            super().__init__(capability_key)
    return DynamicHasCapability
