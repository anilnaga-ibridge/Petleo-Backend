from rest_framework import permissions


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access only to organization admins.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # In Provider Service, request.user is a VerifiedUser object
        role = getattr(request.user, 'role', '')
        if not role:
            return False
            
        return role.upper() == 'ORGANIZATION'


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

        verified_user = request.user
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
