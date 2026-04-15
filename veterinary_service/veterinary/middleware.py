
import threading
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import VeterinaryStaff, StaffClinicAssignment

from .authentication import ShadowUserAuthentication

_thread_locals = threading.local()

def get_current_user_id():
    return getattr(_thread_locals, 'user_id', None)

def get_current_clinic_id():
    return getattr(_thread_locals, 'clinic_id', None)

class VeterinaryPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to attach VeterinaryStaff permissions to request.user.
    Also stores user_id in thread-local for signals.
    Supports multi-clinic context resolution via assignments.
    """
    def process_request(self, request):
        from .log_utils import log_mw as log

        log("--- Request Started ---")
        log(f"Path: {request.path}")
        log(f"Method: {request.method}")

        # 1. Manual JWT Auth
        if not request.user or not request.user.is_authenticated:
            log("User not authenticated. Attempting Manual Shadow Auth.")
            try:
                auth = ShadowUserAuthentication()
                header = auth.get_header(request)
                if header:
                    log("Token header found.")
                    raw_token = auth.get_raw_token(header)
                    if raw_token:
                        validated_token = auth.get_validated_token(raw_token)
                        user = auth.get_user(validated_token)
                        request.user = user
                        request.auth = validated_token  # Set request.auth so we can access claims
                        log(f"Manual Auth Success. User: {user.username}")
                    else:
                        log("Header found but raw token invalid.")
                else:
                    log("No auth header found.")
            except Exception as e:
                log(f"Manual Auth Failed: {e}")
                # ... existing debug decode ...

        if not request.user or not request.user.is_authenticated:
            log("User still anonymous. Exiting.")
            _thread_locals.user_id = None
            return

        try:
            auth_user_id = request.user.username 
            _thread_locals.user_id = auth_user_id
            log(f"Authenticated User ID (username): {auth_user_id}")
            # Extract Role from Token if not on User object
            log(f"Auth Payload: {request.auth}")
            token_role = None
            if request.auth:
                if isinstance(request.auth, dict):
                    token_role = request.auth.get('role')
                else:
                    # AccessToken or similar
                    try:
                        token_role = request.auth.get('role')
                    except:
                        token_role = getattr(request.auth, 'payload', {}).get('role')
            
            user_role = str(getattr(request.user, 'role', token_role or '')).upper()
            request.user.role = user_role 
            log(f"Resolved User Role: {user_role}")
            
            target_clinic_id = request.headers.get('X-Clinic-ID') or request.GET.get('clinic_id')
            log(f"Target Clinic ID: {target_clinic_id}")

            # 3. IDENTITY PRIORITY: Organization/Individual Provider takes precedence
            if user_role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
                log(f"Processing as {user_role}")
                from .models import Clinic
                clinic = None
                if target_clinic_id:
                    # STRICT: Only select the clinic if explicitly requested and owned by this org
                    log(f"Attempting Strict Clinic Match: OrgID={auth_user_id}, ClinicID={target_clinic_id}")
                    clinic = Clinic.objects.filter(organization_id=str(auth_user_id), id=target_clinic_id).first()
                
                if not clinic:
                    # FALLBACK: Find any clinic owned by this org (when no clinic header is sent)
                    clinic = Clinic.objects.filter(organization_id=str(auth_user_id)).first()
                    if clinic:
                        log(f"No X-Clinic-ID header. Using first owned clinic: {clinic.id}")
                
                if clinic: # Moved clinic check here to ensure permissions are set only if clinic is found/owned
                    # COMPLETE AUTOMATION: Owners inherently pass RBAC capability checks in the decorators and permissions
                    # so we no longer inject a hardcoded list of capabilities here.
                    request.user.permissions = []
                    request.user.clinic_id = clinic.id
                else:
                    log(f"Clinic NOT FOUND or NOT OWNED. target_clinic_id was: {target_clinic_id}")
                    request.user.clinic_id = None
                    request.user.permissions = []
                request.user.staff_profile = None

            else:
                # 4. Fallback to Staff Logic
                staff = VeterinaryStaff.objects.filter(auth_user_id=auth_user_id).first()
                log(f"Staff Profile Found: {staff is not None}")

                if staff:
                    assignment = None
                    if target_clinic_id:
                        assignment = StaffClinicAssignment.objects.filter(
                            staff=staff, clinic_id=target_clinic_id, is_active=True
                        ).first()
                    
                    if not assignment:
                        assignment = StaffClinicAssignment.objects.filter(
                            staff=staff, is_primary=True, is_active=True
                        ).first()
                        log(f"Using Primary Assignment: {assignment is not None}")

                    if assignment:
                        # [FIX] Fallback to role-based permissions if assignment perms are empty
                        perms = assignment.permissions
                        assigned_role = assignment.role or staff.role
                        
                        # [SENIOR DEV FIX] If local assignment is generic 'employee', prefer specific role from token
                        if assigned_role.lower() == 'employee' and token_role:
                            log(f"Overriding generic 'employee' role with specific token role: {token_role}")
                            assigned_role = token_role

                        if not perms and assigned_role:
                            from .services import RolePermissionService
                            perms = RolePermissionService.get_permissions_for_role(assigned_role)
                            log(f"Empty perms in assignment. Falling back to role '{assigned_role}' defaults.")
                        
                        # Ensure consultation capability is present for relevant clinical roles
                        if assigned_role and assigned_role.lower() in ['doctor', 'senior doctor', 'veterinary doctor', 'admin', 'practice manager']:
                            if isinstance(perms, list) and 'VETERINARY_CONSULTATION' not in perms:
                                perms.append('VETERINARY_CONSULTATION')
                                log(f"Injected VETERINARY_CONSULTATION for role: {assigned_role}")
                        
                        request.user.permissions = perms
                        request.user.clinic_id = assignment.clinic_id
                        request.user.role = assigned_role
                        log(f"Assignment Active. Clinic ID set to: {assignment.clinic_id}")
                    else:
                        log("No Assignment Found.")
                        # Legacy fallback
                        if staff.clinic:
                             request.user.clinic_id = staff.clinic.id
                             log(f"Legacy Fallback used. Clinic ID: {staff.clinic.id}")
                        else:
                             request.user.clinic_id = None
                             log("Legacy Fallback failed. No clinic.")
                        
                        request.user.permissions = staff.permissions
                        request.user.role = staff.role
                    
                    request.user.staff_profile = None
                
                # Store clinic_id in thread-local for Managers
                if hasattr(request.user, 'clinic_id'):
                    _thread_locals.clinic_id = request.user.clinic_id
                else:
                    _thread_locals.clinic_id = None
                
        except Exception as e:
            import traceback
            error_msg = f"Middleware Error: {e}\n{traceback.format_exc()}"
            log(error_msg)
            request.user.permissions = []
            _thread_locals.user_id = None

    def process_response(self, request, response):
        _thread_locals.user_id = None
        _thread_locals.clinic_id = None
        return response
