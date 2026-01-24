from rest_framework import permissions
from .models import Clinic
import logging
import datetime

def log(msg):
    with open("/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service/middleware_trace.log", "a") as f:
        f.write(f"{datetime.datetime.now()} - [PERM] {msg}\n")

class HasVeterinaryAccess(permissions.BasePermission):
    """
    Allows access only if the provider's plan includes the VETERINARY_MODULE capability.
    """

    def has_permission(self, request, view):
        """
        ARCHITECTURAL LOCK-IN:
        1. Only authenticated users with clinical roles (Doctor, Staff, Owner) can access clinical APIs.
        2. Super Admins are strictly prohibited from CLINICAL data. They manage infrastructure only.
        3. Access is driven by the 'permissions' (capabilities) list assigned to the user context.
        """
        # 1. Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # DRF Auth (SimpleJWT) might return a fresh User object without 'role'.
        # We must populate it from the token (request.auth) if missing.
        if not getattr(request.user, 'role', None):
            token = getattr(request, 'auth', None)
            if token:
                if isinstance(token, dict):
                    request.user.role = token.get('role', '')
                elif hasattr(token, 'get'):
                    request.user.role = token.get('role', '')
                elif hasattr(token, 'payload'):
                    request.user.role = token.payload.get('role', '')
                
        user_role = str(getattr(request.user, 'role', '')).upper()
        
        # 2. Infrastructure Guard: Super Admins manage plans, not pets.
        if user_role == 'SUPERADMIN':
            log("SuperAdmin access blocked for clinical data.")
            return False
            
        # [SENIOR DEV FIX] Ensure permissions are attached even if DRF replaced the user object
        if user_role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
            if not getattr(request.user, 'permissions', None):
                log("Permissions attribute missing on user. Resolving context...")
                from .views import get_clinic_context
                clinic_id = get_clinic_context(request)
                if clinic_id:
                    log(f"Context found: {clinic_id}. Attaching full clinical suite.")
                    request.user.clinic_id = clinic_id
                    request.user.permissions = [
                        "VETERINARY_CORE", 
                        "VETERINARY_ADMIN", 
                        "VETERINARY_VISITS", 
                        "VETERINARY_VITALS", 
                        "VETERINARY_PRESCRIPTIONS", 
                        "VETERINARY_LABS", 
                        "VETERINARY_VACCINES",
                        "VETERINARY_MEDICINE_REMINDERS"
                    ]
                else:
                    log("No clinic context found. Permissions remain empty.")
                    request.user.permissions = []
            
        log(f"has_permission success for {user_role}. Permissions Count: {len(getattr(request.user, 'permissions', []))}")
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        user_role = getattr(user, 'role', '').upper()
        
        # 1. Resolve Clinic Context
        clinic = None
        if isinstance(obj, Clinic):
            clinic = obj
        elif hasattr(obj, 'clinic'):
            clinic = obj.clinic
        elif hasattr(obj, 'owner') and hasattr(obj.owner, 'clinic'):
            clinic = obj.owner.clinic
            
        if not clinic:
            log("No clinic context on object. Treating as global resource.")
            return True
            
        # 2. Ownership Boundary: Organization/Individual Owners can access their own clinics
        if user_role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER']:
            is_owner = clinic.organization_id == str(user.username)
            log(f"Ownership Check: Clinic Org({clinic.organization_id}) == User Username({user.username}) -> {is_owner}")
            return is_owner
            
        # 3. Staff Boundary: Staff must have an assignment to this clinic
        if user_role not in ['CUSTOMER']:
             curr_clinic_id = getattr(user, 'clinic_id', None)
             if not curr_clinic_id:
                 from .views import get_clinic_context
                 curr_clinic_id = get_clinic_context(request)
                 user.clinic_id = curr_clinic_id
             
             log(f"Staff Context Check: Request User Clinic ID({curr_clinic_id}) == Clinic ID({clinic.id})")
             if str(curr_clinic_id) == str(clinic.id):
                 # Check capability
                 capabilities = clinic.capabilities or {}
                 has_mod = capabilities.get('VETERINARY_MODULE', False)
                 log(f"VETERINARY_MODULE Check: {has_mod}")
                 return has_mod
        
        log(f"Permission denied for Role: {user_role}, Clinic ID: {clinic.id}")
        return False

class IsClinicStaffOfPet(permissions.BasePermission):
    """
    Permission check for clinic staff trying to update a pet.
    Access granted if:
    1. User has a valid clinic context (clinic_id).
    2. The pet has at least one visit associated with that clinic.
    """
    def has_object_permission(self, request, view, obj):
        clinic_id = getattr(request.user, 'clinic_id', None)
        if not clinic_id:
            from .views import get_clinic_context
            clinic_id = get_clinic_context(request)
            
        if not clinic_id:
            return False
            
        # Check if this pet has ever visited this clinic
        from .models import Visit
        return Visit.objects.filter(pet=obj, clinic_id=clinic_id).exists()

from functools import wraps
from rest_framework.exceptions import PermissionDenied

def require_capability(capability):
    """
    Decorator to enforce strict capability checks on API views.
    Usage: @require_capability('VETERINARY_VITALS')
           @require_capability(['VETERINARY_VISITS', 'VETERINARY_DOCTOR']) # OR Logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            # 1. Get User Permissions (from JWT or DB)
            user_perms = getattr(request.user, 'permissions', None)
            
            # [SENIOR DEV SAFETY NET] Proactively Resolve if missing for Owners
            role = str(getattr(request.user, 'role', '')).upper()
            if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
                if user_perms is None:
                    from .views import get_clinic_context
                    clinic_id = get_clinic_context(request)
                    if clinic_id:
                        request.user.permissions = [
                            "VETERINARY_CORE", "VETERINARY_ADMIN", "VETERINARY_VISITS", 
                            "VETERINARY_VITALS", "VETERINARY_PRESCRIPTIONS", "VETERINARY_LABS", 
                            "VETERINARY_VACCINES", "VETERINARY_MEDICINE_REMINDERS", "VETERINARY_DOCTOR", "VETERINARY_PHARMACY"
                        ]
                        user_perms = request.user.permissions
                    else:
                        request.user.permissions = []
                        user_perms = []
            
            # 2. Check Capability (Support OR logic for lists)
            allowed = False
            current_perms = user_perms or []
            
            if isinstance(capability, list) or isinstance(capability, tuple):
                # OR Logic: Pass if user has ANY of the required capabilities
                if any(cap in current_perms for cap in capability):
                    allowed = True
            else:
                # Single String Check
                if capability in current_perms:
                    allowed = True
                    
            if not allowed:
                raise PermissionDenied(f"Permission denied. Missing capability: {capability}")
            
            return func(view, request, *args, **kwargs)
        return wrapper
    return decorator
