from rest_framework import permissions
from .models import Pet


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow pet owners to access their pets.
    Providers can only view during bookings (future implementation).
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # request.user is a PetOwnerProfile instance
        user = request.user
        
        # For Pet objects
        if isinstance(obj, Pet):
            # Check owner
            if obj.owner != user:
                return False
            
            # Rule: Block modification if Deceased (except for status change or read)
            if obj.status == 'DECEASED' and request.method not in permissions.SAFE_METHODS:
                # Allow changing status FROM deceased? Usually not, but let's be strict
                return False
                
            return True
        
        # For PetMedicalProfile and PetDocument objects
        if hasattr(obj, 'pet'):
            if obj.pet.owner != user:
                return False
            
            # Block data modification if pet is deceased
            if obj.pet.status == 'DECEASED' and request.method not in permissions.SAFE_METHODS:
                return False
                
            return True
        
        return False
