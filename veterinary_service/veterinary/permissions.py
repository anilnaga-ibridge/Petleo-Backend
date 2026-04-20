from rest_framework import permissions
from .models import Clinic
import logging
import datetime

from .log_utils import log_perm as log

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
                    log(f"Context found: {clinic_id}. Attaching owner implicit access.")
                    request.user.clinic_id = clinic_id
                    # Complete Automation: Owners implicitly pass capability checks, so no hardcoded list needed here.
                    request.user.permissions = [] 
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
        if clinic.organization_id == str(user.username):
            log(f"Global Ownership Match: Clinic Org({clinic.organization_id}) == User UUID({user.username}) -> ACCESS GRANTED")
            return True
            
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
                 # [SENIOR DEV FIX] Bypass VETERINARY_MODULE check for Service-Specific Visits (e.g. Grooming)
                 if hasattr(obj, 'service_id') and obj.service_id:
                     log(f"Service Visit Detected ({obj.service_id}). Allowing access.")
                     return True

                 capabilities = clinic.capabilities or {}
                 # [SENIOR DEV FIX] Robust check for VETERINARY_MODULE:
                 # 1. Direct Key check (Legacy/Config)
                 # 2. Key inside 'permissions' list (Sync-based)
                 # 3. Fallback to VETERINARY_CORE
                 has_mod = capabilities.get('VETERINARY_MODULE', False)
                 
                 if not has_mod and 'permissions' in capabilities:
                     has_mod = 'VETERINARY_MODULE' in capabilities['permissions'] or 'VETERINARY_CORE' in capabilities['permissions']
                 
                 log(f"VETERINARY_MODULE Check: {has_mod}")
                 return has_mod
        
        log(f"Permission denied for Role: {user_role}, Clinic ID: {clinic.id}")
        return False

class VeterinaryCheckoutPermission(permissions.BasePermission):
    """
    Strict permission for processing billing and visit closure.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_perms = getattr(request.user, 'permissions', [])
        return "VETERINARY_CHECKOUT" in user_perms

VET_BRIDGE = {
    "VISITS": "VETERINARY_VISITS",
    "PATIENTS": "VETERINARY_PATIENTS",
    "VITALS": "VETERINARY_VITALS",
    "VETERINARY_ASSISTANT": "VETERINARY_VITALS",
    "DOCTOR_STATION": "VETERINARY_DOCTOR",
    "PHARMACY": "VETERINARY_PHARMACY",
    "PHARMACY_STORE": "VETERINARY_PHARMACY_STORE",
    "LABS": "VETERINARY_LABS",
    "SCHEDULE": "VETERINARY_SCHEDULE",
    "OFFLINE_VISITS": "VETERINARY_OFFLINE_VISIT",
    "ONLINE_CONSULT": "VETERINARY_ONLINE_CONSULT",
    "MEDICINE_REMINDERS": "VETERINARY_MEDICINE_REMINDERS",
    "CLINIC_SETTINGS": "VETERINARY_ADMIN_SETTINGS",
    "METADATA_MANAGEMENT": "VETERINARY_METADATA"
}

# Bidirectional mapping
REVERSE_VET_BRIDGE = {v: k for k, v in VET_BRIDGE.items()}

class HasGranularCapability(permissions.BasePermission):
    """
    Checks if the user possesses the specific granular capability and the required action flag.
    Supports bridging between legacy keys (e.g. VISITS) and modern keys (e.g. VETERINARY_VISITS).
    """
    def __init__(self, capability_key=None):
        self.capability_key = capability_key

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        role = str(getattr(request.user, 'role', '')).upper()
        
        # COMPLETE AUTOMATION: Owner Bypass. Organizations inherently have full access to their clinics.
        if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
            return True

        user_perms = getattr(request.user, 'permissions', [])
        
        log(f"HasGranularCapability({self.capability_key}).has_permission: user_perms={user_perms}")
        
        if not user_perms:
            return False

        # Standardize search keys (bridged)
        search_keys = [self.capability_key]
        if self.capability_key in VET_BRIDGE:
            search_keys.append(VET_BRIDGE[self.capability_key])
        if self.capability_key in REVERSE_VET_BRIDGE:
            search_keys.append(REVERSE_VET_BRIDGE[self.capability_key])

        # Determine required flag based on HTTP Method
        required_flag = 'can_view'
        if request.method == 'POST': required_flag = 'can_create'
        elif request.method in ['PUT', 'PATCH']: required_flag = 'can_edit'
        elif request.method == 'DELETE': required_flag = 'can_delete'

        # 3. Check for match in list of objects
        for p in user_perms:
            # Determine required suffix based on HTTP Method for strict string matching
            suffix = required_flag.upper().replace('CAN_', '_') # e.g. _VIEW, _CREATE, _EDIT, _DELETE
            
            # Handle both flat strings (Legacy/Owner/Expanded) and Objects (Staff)
            if isinstance(p, str):
                for sk in search_keys:
                    # 1. Base Match (Unrestricted access for legacy strings like 'VISITS')
                    if p == sk or ('.' in sk and p == f"{sk.split('.')[0]}.*"):
                        return True
                    
                    # 2. Granular Suffix Match (Strict action-based access for strings like 'VETERINARY_VISITS_CREATE')
                    if p == f"{sk}{suffix}":
                        return True
                    
            elif isinstance(p, dict):
                p_key = p.get('capability_key')
                for sk in search_keys:
                    if p_key == sk or ('.' in sk and p_key == f"{sk.split('.')[0]}.*"):
                        return p.get(required_flag, False)
                
        return False

def require_granular_capability(capability_key):
    """Factory for DRF permission_classes."""
    class DynamicHasCapability(HasGranularCapability):
        def __init__(self):
            super().__init__(capability_key)
    return DynamicHasCapability

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
    Supports granular 'module.action' codes and 'module.*' wildcards.
    Usage: @require_capability('vitals.create')
           @require_capability(['appointment.create', 'appointment.view']) # OR Logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            # 1. Get User Permissions
            user_perms = getattr(request.user, 'permissions', None)
            
            # [SENIOR DEV SAFETY NET] Proactively Resolve if missing for Owners
            role = str(getattr(request.user, 'role', '')).upper()
            if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
                # COMPLETE AUTOMATION: Owner Bypass. No hardcoded arrays.
                return func(view, request, *args, **kwargs)
            
            # 2. Check Capability
            allowed = False
            current_perms = user_perms or []
            
            req_caps = [capability] if isinstance(capability, str) else capability
            
            # Determine required flag based on HTTP Method
            required_flag = 'can_view'
            if request.method == 'POST': required_flag = 'can_create'
            elif request.method in ['PUT', 'PATCH']: required_flag = 'can_edit'
            elif request.method == 'DELETE': required_flag = 'can_delete'

            for req_cap in req_caps:
                # Standardize search keys (bridged)
                search_keys = [req_cap]
                if req_cap in VET_BRIDGE:
                    search_keys.append(VET_BRIDGE[req_cap])
                if req_cap in REVERSE_VET_BRIDGE:
                    search_keys.append(REVERSE_VET_BRIDGE[req_cap])

                for p in current_perms:
                    # Handle flat strings (Legacy/Owner)
                    if isinstance(p, str):
                        for sk in search_keys:
                            if p == sk or ('.' in sk and p == f"{sk.split('.')[0]}.*"):
                                allowed = True
                                break
                    # Handle dictionaries (Staff with granular flags)
                    elif isinstance(p, dict):
                        p_key = p.get('capability_key')
                        for sk in search_keys:
                            if p_key == sk or ('.' in sk and p_key == f"{sk.split('.')[0]}.*"):
                                if p.get(required_flag, False):
                                    allowed = True
                                    break
                    if allowed: break
                if allowed: break
                        
            if not allowed:
                log(f"PERMISSION DENIED in require_capability: user_perms={user_perms}, looking for {req_caps}")
                raise PermissionDenied(f"Permission denied. Missing or insufficient capability for: {capability}")
            
            return func(view, request, *args, **kwargs)
        return wrapper
    return decorator


def has_capability_access(user, required_cap, required_action='view'):
    """
    Standardized Authorization Check for Veterinary Capabilities.
    
    1. Handles Role-based Bypasses (Organizations/Providers have full access).
    2. Supports Granular Capability Objects (with can_view, can_create, etc.).
    3. Supports Legacy Flat String Permissions.
    
    Returns: bool (True if authorized, False otherwise)
    """
    if not user or not user.is_authenticated:
        return False

    role = str(getattr(user, 'role', '')).upper()

    # 1. OWNER BYPASS: Organizations and Providers have implicit full access to their clinics
    if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
        return True

    # 2. GRANULAR CHECK: Evaluate staff-level permissions
    user_perms = getattr(user, 'permissions', [])
    if not user_perms:
        return False

    # Standardize the required flag name
    action_flag = f"can_{required_action.lower()}"
    # Standardize the required suffix for flat strings (e.g. _VIEW)
    suffix = f"_{required_action.upper()}"

    for p in user_perms:
        # Standardize search keys (bridged)
        search_keys = [required_cap]
        if required_cap in VET_BRIDGE:
            search_keys.append(VET_BRIDGE[required_cap])
        if required_cap in REVERSE_VET_BRIDGE:
            search_keys.append(REVERSE_VET_BRIDGE[required_cap])

        # A. Handle Granular Object (Preferred)
        if isinstance(p, dict):
            p_key = p.get('capability_key')
            for sk in search_keys:
                if p_key == sk or ('.' in sk and p_key == f"{sk.split('.')[0]}.*"):
                    if p.get(action_flag, False):
                        return True

        # B. Handle Flat String (Heritage / Re-resolved)
        elif isinstance(p, str):
            for sk in search_keys:
                # Universal match or exact match or suffix match
                if p == sk or p == f"{sk}{suffix}" or ('.' in sk and p == f"{sk.split('.')[0]}.*"):
                    return True

    return False
