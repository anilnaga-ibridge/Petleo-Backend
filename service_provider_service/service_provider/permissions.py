from .models import ProviderPermission

def user_has_permission(user, permission_code):
    """
    Check if the verified user has the specific permission.
    """
    if not user or not user.is_authenticated:
        return False
        
    # If user is superuser (Django admin), allow all? 
    # Maybe not, as this is for Provider context.
    
    # Check if user has the permission
    return ProviderPermission.objects.filter(
        verified_user=user, 
        permission_code=permission_code
    ).exists()
