
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class ShadowUserAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that creates a local shadow user 
    if it doesn't exist in the database. 
    Matches the pattern used in super_admin_service.
    """
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
            
        user, validated_token = result
        
        # [SENIOR DEV FIX] Attach Clinic Context and Permissions globally for DRF
        target_clinic_id = request.headers.get('X-Clinic-ID') or request.GET.get('clinic_id')
        role = str(validated_token.get('role', '')).upper()
        user_id = validated_token.get('user_id')

        from .permissions import log as perm_log
        perm_log(f"ShadowAuth: Role={role}, UserID={user_id}, TargetClinic={target_clinic_id}")

        # 1. Organization/Individual Owner Logic
        if role in ['ORGANIZATION', 'INDIVIDUAL', 'PROVIDER', 'ORGANIZATION_PROVIDER', 'ORGANIZATION_ADMIN']:
            from .models import Clinic
            clinic = None
            if target_clinic_id:
                clinic = Clinic.objects.filter(organization_id=str(user_id), id=target_clinic_id).first()
            
            if clinic:
                perm_log(f"ShadowAuth: Clinic found: {clinic.name}")
                user.clinic_id = clinic.id
                
                # [FIX] Pull from Clinic.capabilities instead of hardcoded list
                raw_perms = clinic.capabilities or {}
                if isinstance(raw_perms, list):
                    user.permissions = raw_perms
                else:
                    user.permissions = raw_perms.get('permissions', [])

                if "VETERINARY_CORE" not in user.permissions:
                    user.permissions.append("VETERINARY_CORE")
            else:
                perm_log("ShadowAuth: Clinic NOT found or NOT owned.")
                user.clinic_id = None
                user.permissions = [] # No clinic selected = No clinical permissions for Org
        
        # 2. Staff Logic
        if not hasattr(user, 'permissions') or not user.permissions:
            user.permissions = []
            
            # Fetch Staff Profile
            from .models import VeterinaryStaff, StaffClinicAssignment
            perm_log(f"\n{'='*80}")
            perm_log(f"🔍 STAFF PERMISSION LOADING: user_id={user_id}")
            perm_log(f"{'='*80}")
            
            staff = VeterinaryStaff.objects.filter(auth_user_id=user_id).first()
            
            if staff:
                perm_log(f"✅ Staff Profile Found: ID={staff.id}, Role={staff.role}")
                perm_log(f"📋 Staff Base Permissions: {staff.permissions}")
                
                assignment = None
                if target_clinic_id:
                    perm_log(f"🎯 Looking for clinic-specific assignment: clinic_id={target_clinic_id}")
                    assignment = StaffClinicAssignment.objects.filter(
                        staff=staff, clinic_id=target_clinic_id, is_active=True
                    ).first()
                
                if not assignment:
                    # Fallback to primary if no clinic targeted, or if target invalid
                    perm_log(f"🏠 Falling back to primary assignment")
                    assignment = StaffClinicAssignment.objects.filter(
                        staff=staff, is_primary=True, is_active=True
                    ).first()
                
                if assignment:
                    user.permissions = assignment.permissions
                    user.clinic_id = assignment.clinic_id
                    user.role = assignment.role or staff.role
                    perm_log(f"✅ Assignment Found:")
                    perm_log(f"   - Clinic ID: {assignment.clinic_id}")
                    perm_log(f"   - Role: {assignment.role}")
                    perm_log(f"   - Permissions: {assignment.permissions}")
                    perm_log(f"   - Permission Count: {len(user.permissions)}")
                    perm_log(f"   - Is Primary: {assignment.is_primary}")
                    perm_log(f"   - Is Active: {assignment.is_active}")
                else:
                    # Fallback to Staff Base permissions
                    user.permissions = staff.permissions
                    user.role = staff.role
                    user.clinic_id = staff.clinic.id if staff.clinic else None
                    perm_log(f"⚠️ No Assignment Found. Using Base Staff Permissions:")
                    perm_log(f"   - Permissions: {staff.permissions}")
                    perm_log(f"   - Permission Count: {len(user.permissions)}")
                    perm_log(f"   - Clinic ID: {user.clinic_id}")
                    
            else:
                perm_log("❌ No Staff Profile found for this user")
        
        perm_log(f"🎯 FINAL AUTH PERMISSIONS: {user.permissions}")
        perm_log(f"{'='*80}\n")
        
        return user, validated_token

    def get_user(self, validated_token):
        user_id = validated_token.get("user_id")
        email = validated_token.get("email")
        token_role = validated_token.get("role")

        if not user_id:
            raise AuthenticationFailed(_("Token missing user_id claim"), code="no_user_id")

        try:
            # We store the central UUID in the 'username' field 
            user = User.objects.get(username=str(user_id))
        except User.DoesNotExist:
            user = User.objects.create(
                username=str(user_id),
                email=email or "",
                is_active=True,
                is_staff=True
            )
            
        # Attach role from token
        user.role = token_role
        return user
