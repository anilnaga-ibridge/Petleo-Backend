
import threading
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import VeterinaryStaff, StaffClinicAssignment

from .authentication import ShadowUserAuthentication

_thread_locals = threading.local()

def get_current_user_id():
    return getattr(_thread_locals, 'user_id', None)

class VeterinaryPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to attach VeterinaryStaff permissions to request.user.
    Also stores user_id in thread-local for signals.
    Supports multi-clinic context resolution via assignments.
    """
    def process_request(self, request):
        log_file = "/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service/middleware_trace.log"
        def log(msg):
            try:
                with open(log_file, "a") as f:
                    f.write(f"{timezone.now()} - {msg}\n")
            except:
                pass

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
                
                if clinic:
                    log(f"Clinic MATCHED: {clinic.name}")
                    request.user.clinic_id = clinic.id
                    # Owners/Admins get all clinical capabilities
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
                        request.user.permissions = assignment.permissions
                        request.user.clinic_id = assignment.clinic_id
                        request.user.role = assignment.role or staff.role
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
                    
                    request.user.staff_profile = staff
                else:
                    log("User is neither Org/Ind nor Staff.")
                    request.user.permissions = []
                    request.user.staff_profile = None
                    request.user.clinic_id = None
                
        except Exception as e:
            import traceback
            error_msg = f"Middleware Error: {e}\n{traceback.format_exc()}"
            log(error_msg)
            request.user.permissions = []
            _thread_locals.user_id = None

    def process_response(self, request, response):
        _thread_locals.user_id = None
        return response
