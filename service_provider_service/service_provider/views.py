from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, action
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
import logging
import json

logger = logging.getLogger(__name__)


from .models import (
    ServiceProvider, 
    VerifiedUser,
    AllowedService,
    Capability,
    ProviderRole,
    ProviderRoleCapability,
    OrganizationEmployee,
    PermissionAuditLog,
    ProviderRating,
    ConsultationType,
)
from .serializers import (
    ServiceProviderSerializer, 
    CapabilitySerializer,
    ProviderRoleSerializer,
    PublicProviderSerializer,
    PublicProviderDetailSerializer,
    ProviderRatingSerializer,
    OrganizationEmployeeSerializer,
    MinimalEmployeeSerializer,
)

from provider_dynamic_fields.models import (
    LocalFieldDefinition,
    LocalDocumentDefinition,
    ProviderFieldValue,
    ProviderDocument
)
from provider_dynamic_fields.serializers import ProviderDocumentSerializer
from service_provider.kafka_producer import publish_user_profile_updated

class ServiceProviderProfileView(APIView):
    """
    Unified View for Service Provider Profile.
    Handles core fields (avatar, banner) and dynamic fields/documents.
    """

    def get(self, request):
        """Fetch the current authenticated provider's profile, including dynamic fields."""
        # Get auth_user_id from query params or current user
        auth_user_id = request.GET.get('user') or request.GET.get('auth_user_id')
        
        if auth_user_id:
            try:
                verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
            except VerifiedUser.DoesNotExist:
                # [JIT FIX] If authenticated but missing locally, create it
                if request.user.is_authenticated and str(request.user.id) == str(auth_user_id):
                    verified_user = VerifiedUser.objects.create(
                        auth_user_id=auth_user_id,
                        email=getattr(request.user, 'email', None),
                        full_name=getattr(request.user, 'full_name', None),
                        role=getattr(request.user, 'role', 'User')
                    )
                    logger.info(f"✅ JIT Created VerifiedUser for {verified_user.email}")
                else:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            verified_user = request.user
            # [JIT FIX] Handle TransientUser (not in DB)
            if not isinstance(verified_user, VerifiedUser):
                verified_user, created = VerifiedUser.objects.get_or_create(
                    auth_user_id=verified_user.id,
                    defaults={
                        "email": verified_user.email,
                        "full_name": verified_user.full_name,
                        "role": verified_user.role or 'User'
                    }
                )
                if created:
                    logger.info(f"✅ JIT Created VerifiedUser (from Request User) for {verified_user.email}")

        # Target for dynamic fields
        target = request.GET.get("target") or getattr(verified_user, "provider_type", None)
        if not target:
            # Fallback based on role
            role = (str(verified_user.role) if verified_user.role else "").lower()
            if role == 'superadmin': target = 'superadmin'
            elif role == 'organization': target = 'organization'
            elif role == 'employee': target = 'employee'
            else: target = 'individual'

        # 1. Fetch Dynamic Field Definitions
        field_definitions_qs = LocalFieldDefinition.objects.filter(target=target).order_by('order')
        
        # Get provider record for field mapping
        provider = getattr(verified_user, 'provider_profile', None)

        # 2. Merge with Values
        fields_data = []
        for fd in field_definitions_qs:
            field_id = str(fd.id)
            try:
                saved_value = ProviderFieldValue.objects.get(verified_user=verified_user, field_id=field_id)
            except ProviderFieldValue.DoesNotExist:
                saved_value = None

            if saved_value and saved_value.file:
                metadata = {
                    "name": saved_value.file.name.split("/")[-1],
                    "size": saved_value.file.size,
                    "content_type": saved_value.metadata.get("content_type", ""),
                    "file_url": request.build_absolute_uri(saved_value.file.url),
                }
                value = None
            else:
                metadata = saved_value.metadata if saved_value else {}
                value = saved_value.value if saved_value else None

                # Source of Truth for basic fields
                is_org = provider and provider.provider_type == 'ORGANIZATION'
                clinic_name = None
                if is_org:
                    try:
                        from .models import ProviderProfile
                        p_profile = getattr(provider, 'detailed_profile', None)
                        clinic_name = p_profile.clinic_name if p_profile else None
                    except Exception:
                        pass

                if fd.name == "first_name":
                    full_name = verified_user.full_name or ""
                    # [ENHANCEMENT] If full_name is likely the clinic name (no separate clinic_name exists), 
                    # don't split it into personal name fields for owners.
                    if is_org and not clinic_name and full_name:
                        value = ""
                    else:
                        value = full_name.split(" ", 1)[0] if full_name else ""
                elif fd.name == "last_name":
                    full_name = verified_user.full_name or ""
                    if is_org and not clinic_name and full_name:
                        value = ""
                    else:
                        value = full_name.split(" ", 1)[1] if " " in full_name else ""
                elif fd.name == "email":
                    value = verified_user.email
                elif fd.name == "phone_number":
                    value = verified_user.phone_number
                elif fd.name == "organization_name":
                    # Fetch from ProviderProfile.clinic_name
                    if is_org:
                        # Fallback to full_name if clinic_name is empty (initial state)
                        value = clinic_name or verified_user.full_name
                    else:
                        value = None
                elif fd.name == "country":
                    # Fetch from BillingProfile
                    try:
                        from .models import BillingProfile
                        profile = BillingProfile.objects.get(verified_user=verified_user)
                        value = profile.country
                    except (BillingProfile.DoesNotExist, ImportError):
                        value = None

            fields_data.append({
                "id": field_id,
                "name": fd.name,
                "label": fd.label,
                "field_type": fd.field_type,
                "is_required": fd.is_required,
                "options": fd.options,
                "order": fd.order,
                "value": value,
                "metadata": metadata,
            })

        # 3. Handle Avatar and Banner (Core fields)
        avatar_url = verified_user.avatar_url
        banner_url = None
        
        provider = getattr(verified_user, 'provider_profile', None)
        if provider:
            if provider.avatar:
                avatar_url = request.build_absolute_uri(provider.avatar.url)
            if provider.banner_image:
                banner_url = request.build_absolute_uri(provider.banner_image.url)

        # 4. Normalize role for display
        display_role = "User"
        try:
            emp_record = OrganizationEmployee.objects.get(auth_user_id=verified_user.auth_user_id)
            display_role = emp_record.provider_role.name if emp_record.provider_role else emp_record.role
        except OrganizationEmployee.DoesNotExist:
            display_role = verified_user.role or "User"
        
        display_role = (display_role or "").replace("_", " ").title()

        return Response({
            "id": str(provider.id) if provider else None,
            "fullName": verified_user.full_name or verified_user.username or verified_user.email,
            "email": verified_user.email,
            "phoneNumber": verified_user.phone_number,
            "role": display_role,
            "is_superuser": (str(verified_user.role) if verified_user.role else "").lower() == 'superadmin',
            "provider_type": provider.provider_type if provider else None,
            "avatar": avatar_url,
            "banner_image": banner_url,
            "fields": fields_data
        })

    def post(self, request):
        debug_log = []
        def log(msg):
            debug_log.append(f"[{timezone.now()}] {msg}")
            logger.info(msg)

        log(f"📥 Received POST request for {request.data.get('auth_user_id', 'unknown')}")
        
        auth_user_id = request.data.get('auth_user_id')
        if not auth_user_id:
            return Response({"error": "auth_user_id is required"}, status=400)

        # [JIT FIX] Create VerifiedUser if missing during POST
        verified_user, vu_created = VerifiedUser.objects.get_or_create(
            auth_user_id=auth_user_id,
            defaults={
                "email": getattr(request.user, 'email', None),
                "full_name": getattr(request.user, 'full_name', None),
                "role": getattr(request.user, 'role', 'User')
            }
        )
        if vu_created:
            log(f"✅ JIT Created VerifiedUser during POST: {verified_user.email}")

        provider, _ = ServiceProvider.objects.get_or_create(verified_user=verified_user)

        # 1. Parse Fields JSON
        try:
            fields_data = json.loads(request.data.get("fields", "[]"))
        except json.JSONDecodeError:
            return Response({"error": "Invalid fields JSON"}, status=400)

        # 2. Update Dynamic Fields
        for item in fields_data:
            field_id = item.get("field_id")
            value = item.get("value")
            metadata = item.get("metadata", {})
            if not field_id: continue

            # Sync basic fields back to VerifiedUser if named
            try:
                fd = LocalFieldDefinition.objects.get(id=field_id)
                if fd.name == "first_name":
                    parts = (verified_user.full_name or "").split(" ", 1)
                    last = parts[1] if len(parts) > 1 else ""
                    verified_user.full_name = f"{value} {last}".strip()
                elif fd.name == "last_name":
                    parts = (verified_user.full_name or "").split(" ", 1)
                    first = parts[0] if parts else ""
                    verified_user.full_name = f"{first} {value}".strip()
                elif fd.name == "email":
                    verified_user.email = value
                elif fd.name == "phone_number":
                    verified_user.phone_number = value
                elif fd.name == "country":
                    # Update BillingProfile for country
                    from .models import BillingProfile
                    billing, _ = BillingProfile.objects.get_or_create(verified_user=verified_user)
                    billing.country = value
                    billing.save()
                elif fd.name == "organization_name":
                    # Update ProviderProfile.clinic_name
                    from .models import ProviderProfile
                    p_profile, _ = ProviderProfile.objects.get_or_create(provider=provider)
                    p_profile.clinic_name = value
                    p_profile.save()
                elif fd.name.lower() in ["location", "city"]:
                    from .models import BillingProfile
                    billing, _ = BillingProfile.objects.get_or_create(verified_user=verified_user)
                    billing.contact = value
                    billing.save()
                elif fd.name.lower() == "state":
                    from .models import BillingProfile
                    billing, _ = BillingProfile.objects.get_or_create(verified_user=verified_user)
                    billing.state = value
                    billing.save()
            except LocalFieldDefinition.DoesNotExist:
                # [FIX] Auto-create definition for ad-hoc fields (like Language, etc.) if they come with a distinct ID
                # If the ID is UUID-like, it might be a pre-existing definition we just missed? 
                # Or if it's a string like "Language", we treat it as name.
                
                # Check if we can find by name
                if isinstance(field_id, str) and not field_id.isdigit() and len(field_id) < 50:
                    fd, created = LocalFieldDefinition.objects.get_or_create(
                        target=getattr(verified_user, 'provider_type', 'individual') or 'individual',
                        name=field_id,
                        defaults={
                            "label": field_id,
                            "field_type": "text",
                            "order": 999
                        }
                    )
                    if created:
                         log(f"🆕 Auto-created field definition: {field_id}")
                else:
                    continue

            if value is not None:
                ProviderFieldValue.objects.update_or_create(
                    verified_user=verified_user,
                    field_id=field_id,
                    defaults={"value": value, "metadata": metadata}
                )

        # 3. Handle File Uploads
        avatar_file = request.FILES.get('avatar')
        if avatar_file:
            log(f"🖼️ Updating main avatar: {avatar_file.name}")
            provider.avatar = avatar_file
            provider.avatar_size = f"{round(avatar_file.size / 1024, 2)} KB"
            provider.save()
            verified_user.avatar_url = request.build_absolute_uri(provider.avatar.url)
            log(f"✅ Main avatar updated: {verified_user.avatar_url}")

        # 4. Handle Banner Image Upload
        banner_file = request.FILES.get('banner_image')
        if banner_file:
            log(f"🖼️ Updating banner image: {banner_file.name}")
            provider.banner_image = banner_file
            provider.banner_image_size = f"{round(banner_file.size / 1024, 2)} KB"
            provider.save()
            log(f"✅ Banner image updated")

        # Check for dynamic profile_image upload
        for key, files in request.FILES.lists():
            if key in ['avatar', 'banner_image']: continue
            
            upload_file = files[0]
            try:
                fd = LocalFieldDefinition.objects.get(id=key)
                # If this is the profile_image field, sync to main avatar
                if fd.name == "profile_image":
                    log(f"🖼️ Syncing dynamic profile_image to main avatar: {upload_file.name}")
                    provider.avatar = upload_file
                    provider.save()
                    verified_user.avatar_url = request.build_absolute_uri(provider.avatar.url)
                
                # Save to dynamic value
                ProviderFieldValue.objects.update_or_create(
                    verified_user=verified_user,
                    field_id=key,
                    defaults={
                        "file": upload_file,
                        "value": {"filename": upload_file.name},
                        "metadata": {
                            "content_type": getattr(upload_file, "content_type", ""),
                            "size": upload_file.size
                        }
                    }
                )
            except LocalFieldDefinition.DoesNotExist:
                # Handle documents if key matches a document definition
                try:
                    doc_def = LocalDocumentDefinition.objects.get(id=key)
                    ProviderDocument.objects.filter(verified_user=verified_user, definition_id=key).delete()
                    ProviderDocument.objects.create(
                        verified_user=verified_user,
                        definition_id=key,
                        file=upload_file,
                        filename=upload_file.name,
                        content_type=getattr(upload_file, "content_type", ""),
                        size=upload_file.size
                    )
                    log(f"📄 Document uploaded: {doc_def.label}")
                except LocalDocumentDefinition.DoesNotExist:
                    log(f"⚠️ Unknown file key: {key}")

        verified_user.save()
        provider.save()
        
        # Publish to Kafka
        publish_user_profile_updated(
            auth_user_id=verified_user.auth_user_id,
            full_name=verified_user.full_name,
            email=verified_user.email,
            phone_number=verified_user.phone_number,
            role=verified_user.role, # Role preserved!
            avatar_url=verified_user.avatar_url,
            banner_image_url=request.build_absolute_uri(provider.banner_image.url) if provider.banner_image else None
        )

        return Response({
            "message": "Profile updated successfully",
            "debug": debug_log,
            "user_profile": {
                "fullName": verified_user.full_name or verified_user.username or verified_user.email,
                "email": verified_user.email,
                "phoneNumber": verified_user.phone_number,
                "role": getattr(verified_user, 'role', 'User'),
                "provider_type": provider.provider_type if provider else None,
                "clinicName": getattr(getattr(provider, 'detailed_profile', None), 'clinic_name', None),
                "avatar": request.build_absolute_uri(provider.avatar.url) if (provider and provider.avatar) else verified_user.avatar_url
            }
        })

class ServiceProviderDetailView(APIView):
    """
    GET: Fetch service provider profile by auth_user_id.
    """
    permission_classes = [AllowAny]

    def get(self, request, auth_user_id):
        try:
            verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
            provider = ServiceProvider.objects.get(verified_user=verified_user)
            return Response(ServiceProviderSerializer(provider, context={'request': request}).data)
        except (VerifiedUser.DoesNotExist, ServiceProvider.DoesNotExist):
            return Response({"error": "Provider not found"}, status=status.HTTP_404_NOT_FOUND)



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess,
    ProviderTemplateService,
    ProviderTemplateCategory,
    ProviderTemplateFacility,
    ProviderTemplatePricing
)
from .utils import _build_permission_tree

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_permissions(request):
    """
    Returns the effective permissions for the logged-in provider.
    Includes dynamic check for plan validity.
    """
    user = request.user
    
    # Helper to get display role - Calculate EARLY to ensure it's available for error responses
    display_role = getattr(user, 'role', 'User')

    # [DEFINITIVE FIX] Explicit Super Admin Check (Bypasses incorrect 'Individual' role in DB)
    # Super Admins have NO provider subscription and should NEVER go through permission checks.
    # Returning early prevents the subscription path from overwriting user_profile.role with
    # a title-cased 'Super Admin' string which would break frontend routing.
    is_super_admin = (
        str(user.phone_number) == "9876543210" or 
        (hasattr(user, 'role') and str(user.role).lower() == 'superadmin')
    )
    
    if is_super_admin:
        print(f"✅ [Port 8002] Super Admin detected ({user.email}). Returning early with empty permissions.")
        return Response({
            "permissions": [],
            "plan": None,
            "user_profile": {
                "fullName": getattr(user, 'full_name', None) or getattr(user, 'username', None) or getattr(user, 'email', 'Super Admin'),
                "email": getattr(user, 'email', ''),
                "phoneNumber": getattr(user, 'phone_number', None),
                "role": "SUPERADMIN",  # Always use uppercase — matches frontend routing check
                "provider_type": None,
                "provider_id": None,
                "avatar": getattr(user, 'avatar_url', None),
            }
        })
    
    # Get ServiceProvider record for provider_type (needed for both role and avatar)
    provider = None
    try:
        provider = ServiceProvider.objects.filter(verified_user__auth_user_id=user.auth_user_id).first()
    except Exception:
        pass
    
    # Priority 1: Check if user is an employee (they get their assigned role)
    try:
        emp_record = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        if emp_record.provider_role:
             display_role = emp_record.provider_role.name
             print(f"✅ [Port 8002] Resolved role from ProviderRole: {display_role}")
        else:
             print(f"⚠️ [Port 8002] Employee has no ProviderRole. Using legacy role string: {emp_record.role}")
             display_role = emp_record.role or display_role
    except OrganizationEmployee.DoesNotExist:
        # [FIX] Use VerifiedUser.role as the primary source of truth for provider_type.
        # The ServiceProvider.provider_type defaults to INDIVIDUAL on creation (JIT auto-create),
        # which means it may be wrong for users who registered as 'organization'.
        user_role_lower = str(getattr(user, 'role', '') or '').lower()
        
        if user_role_lower in ['organization', 'serviceprovider', 'provider']:
            correct_provider_type = 'ORGANIZATION'
        elif user_role_lower == 'individual':
            correct_provider_type = 'INDIVIDUAL'
        else:
            correct_provider_type = None

        # Auto-fix the DB record if it's incorrect
        if provider and correct_provider_type and provider.provider_type != correct_provider_type:
            print(f"🔧 [Port 8002] Auto-fixing provider_type for {user.email}: {provider.provider_type} → {correct_provider_type}")
            provider.provider_type = correct_provider_type
            provider.save(update_fields=['provider_type'])

        # Priority 2: Check ServiceProvider.provider_type for org/individual owners
        if provider and provider.provider_type:
            display_role = provider.provider_type
            print(f"✅ [Port 8002] Using provider_type as role: {display_role}")
        elif correct_provider_type:
            display_role = correct_provider_type
        # Priority 3: Fallback to user.role
        # (already set above)

    # Normalize role for display (e.g., 'organization' -> 'Organization')
    if display_role:
        display_role = display_role.replace('_', ' ').title()

    # Get avatar
    avatar_url = None
    try:
        # 1. Try ServiceProvider avatar (Primary) - provider already fetched above
        if provider and provider.avatar:
            avatar_url = request.build_absolute_uri(provider.avatar.url)
        
        # 2. Fallback to VerifiedUser.avatar_url (Secondary)
        if not avatar_url and hasattr(user, 'avatar_url') and user.avatar_url:
            avatar_url = user.avatar_url
            # Ensure full URL if it's a relative path
            if avatar_url.startswith('/'):
                avatar_url = request.build_absolute_uri(avatar_url)
    except Exception:
        pass

    if avatar_url:
        print(f"✅ [Port 8002] AVATAR READY for {user.email}: {avatar_url}")
    else:
        print(f"⚠️ [Port 8002] NO AVATAR found for {user.email}")

    # [FIX] Prioritize individual's name for employees and owners
    # VerifiedUser.full_name often contains the Organization Name for org-level accounts.
    full_name = getattr(user, 'full_name', None)
    clinic_name = None
    
    # 1. Resolve Clinic Name for Organizations
    if provider and provider.provider_type == 'ORGANIZATION':
        try:
            from .models import ProviderProfile
            p_profile = getattr(provider, 'detailed_profile', None)
            if p_profile and p_profile.clinic_name:
                clinic_name = p_profile.clinic_name
        except Exception:
            pass

    # 2. Resolve Individual Name from OrganizationEmployee (Staff)
    try:
        emp = OrganizationEmployee.objects.filter(auth_user_id=user.auth_user_id).first()
        if emp and emp.full_name:
            full_name = emp.full_name
            print(f"👤 [Port 8002] Resolved individual name from OrganizationEmployee: {full_name}")
    except Exception:
        pass

    user_profile = {
        "fullName": full_name or getattr(user, 'username', None) or getattr(user, 'email', 'Unknown'),
        "email": getattr(user, 'email', 'Unknown'),
        "phoneNumber": getattr(user, 'phone_number', None),
        "role": display_role,
        "provider_type": provider.provider_type if provider else None,
        "provider_id": str(provider.id) if provider else None,
        "clinicName": clinic_name,
        "avatar": avatar_url
    }

    # Add rating stats for both employees and providers
    try:
        emp = OrganizationEmployee.objects.filter(auth_user_id=user.auth_user_id).first()
        if emp:
            user_profile["average_rating"] = emp.average_rating
            user_profile["total_ratings"] = emp.total_ratings
        elif provider:
            user_profile["average_rating"] = provider.average_rating
            user_profile["total_ratings"] = provider.total_ratings
    except Exception:
        pass
    
    # [LOGGING] Verify what we are sending back to the frontend
    try:
        with open("debug_perms.log", "a") as f:
            f.write(f"👤 [USER_PROFILE] {user.email}: {json.dumps(user_profile, indent=2)}\n")
    except Exception as log_err:
        print(f"❌ Logging error: {log_err}")
    
    # [LOGGING] Verify what we are sending back
    print(f"👤 [Port 8002] User Profile for {user.email}: {user_profile}")

    # 1. Determine the "Subscription Owner"
    # If it's an employee, we check the Organization's subscription.
    subscription_owner = user
    try:
        try:
            employee = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
            
            # ✅ Check if employee is disabled
            if employee.status == 'DISABLED':
                print(f"DEBUG: Employee {user.email} is DISABLED. Revoking access.")
                return Response({
                    "permissions": [], 
                    "plan": None, 
                    "error": "Your account has been disabled by your organization.",
                    "user_profile": user_profile
                })
                
            subscription_owner = employee.organization.verified_user
            print(f"DEBUG: User is employee. Checking Org subscription: {subscription_owner.email}")
        except OrganizationEmployee.DoesNotExist:
            pass

        # 2. Dynamic Plan Validation
        # Check for ANY active subscription
        active_subs = subscription_owner.purchased_plans.filter(is_active=True)
        
        # Filter out expired ones in Python if needed, or use exclude
        valid_sub = None
        for sub in active_subs:
            if not sub.end_date or sub.end_date >= timezone.now():
                valid_sub = sub
                break
        
        if not valid_sub:
            print(f"DEBUG: No valid active subscription found for {subscription_owner.email}")
            return Response({"permissions": [], "plan": None, "user_profile": user_profile})

        print(f"DEBUG: Found valid subscription: {valid_sub.plan_id}")
            
    except Exception as e:
        print(f"Subscription check failed: {e}")
        # In case of error, we fail safe but RETURN USER PROFILE so navbar works
        return Response({"permissions": [], "plan": None, "user_profile": user_profile})

    # 3. Fetch Capabilities using the robust helper
    permissions_list = _build_permission_tree(subscription_owner, request=request)
    
    # [LOGGING] Trace capabilities
    user_perms_set = set()
    is_employee = False
    try:
        # Re-resolve or check if employee was found above
        employee = OrganizationEmployee.objects.filter(auth_user_id=user.auth_user_id).first()
        if employee:
            user_perms_set = employee.get_final_permissions()  # flat set of strings
            is_employee = True
            print(f"🔑 [Port 8002] Employee Permissions (flat): {sorted(list(user_perms_set))}")
        else:
            # Owner — get all granular plan capabilities
            user_perms_set = subscription_owner.get_all_plan_capabilities()
            print(f"🔑 [Port 8002] Owner Permissions (flat): {len(user_perms_set)} keys")
    except Exception as e:
        print(f"❌ Error tracing capabilities: {e}")

    with open("debug_perms.log", "a") as f:
        f.write(f"\n[{timezone.now()}] get_my_permissions | User: {user.email} ({user.auth_user_id})\n")
        f.write(f"Is Employee: {is_employee}\n")
        f.write(f"Subscription Owner: {subscription_owner.email}\n")
        f.write(f"Capabilities: {sorted(list(user_perms_set))}\n")
        f.write(f"Tree Count: {len(permissions_list)}\n")
        f.write(f"Owner Role: {subscription_owner.role}\n")
        for p in permissions_list:
            f.write(f" - {p.get('service_key')} ({p.get('service_name')})\n")

    # --- INJECT DYNAMIC CAPABILITIES (Grooming, Daycare, etc.) ---
    # These might be simple capability keys not yet linked to full Service Templates
    
    # 1. Get all capability keys for the user
    user_caps = set()
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        
        flat_perms = emp.get_final_permissions()  # e.g. {"BOARDING_BASIC_VIEW", ...}
        user_perms_set = flat_perms
        
        # Derive base capability keys (strip action suffix)
        for key in flat_perms:
            for sfx in ['_VIEW', '_CREATE', '_EDIT', '_DELETE']:
                if key.endswith(sfx):
                    user_caps.add(key[:-len(sfx)])
                    break
            else:
                user_caps.add(key)  # no known suffix, add as-is
        
        print(f"   📊 Final Permissions Count: {len(flat_perms)}")
        print(f"   📋 Base Capability Keys: {sorted(list(user_caps))}")
        print(f"{'='*100}\n")
        
        # IMPORTANT: Filter the permission tree by employee capabilities
        print(f"🔍 Filtering permission tree by employee capabilities...")
        print(f"   Tree size before filter: {len(permissions_list)}")
        
        # Build a mapping of known aliases (template name -> capability key)
        SERVICE_KEY_ALIASES = {
            "VETERINARY": "VETERINARY_CORE",
        }
        
        filtered_permissions = []
        for service in permissions_list:
            service_key = service.get('service_key')
            service_name = service.get('service_name')
            
            # Check if this service key (or its alias) is in user_caps
            resolved_key = SERVICE_KEY_ALIASES.get(service_key, service_key)
            
            # Initial permissions for this service (Service-Level)
            svc_can_view = (service_key + "_VIEW" in user_perms_set) or (resolved_key + "_VIEW" in user_perms_set)
            svc_can_create = (service_key + "_CREATE" in user_perms_set) or (resolved_key + "_CREATE" in user_perms_set)
            svc_can_edit = (service_key + "_EDIT" in user_perms_set) or (resolved_key + "_EDIT" in user_perms_set)
            svc_can_delete = (service_key + "_DELETE" in user_perms_set) or (resolved_key + "_DELETE" in user_perms_set)

            print(f"   🔍 Checking service: {service_name} (key: {service_key} → {resolved_key})")
            print(f"      Initial Svc Perms: V={svc_can_view}, C={svc_can_create}, E={svc_can_edit}, D={svc_can_delete}")
            
            # Always filter categories by employee role
            filtered_categories = []
            for category in service.get('categories', []):
                cat_key = category.get('category_key')
                cat_name = category.get('name') or category.get('category_name')
                print(f"         Category: {cat_name} (key: {cat_key})")
                
                # Check if employee has any permission key matching this category
                if cat_key:
                    # [PRODUCTION BRIDGE] Align short DB keys (VISITS) with full capability keys (VETERINARY_VISITS)
                    # This ensures clinical modules are correctly revealed to staff even if DB keys are legacy.
                    matched_perms = [f"{cat_key}_VIEW", f"{cat_key}_CREATE", f"{cat_key}_EDIT", f"{cat_key}_DELETE"]
                    
                    if service_key == "VETERINARY_CORE" and not cat_key.startswith("VETERINARY_"):
                        EXT_TO_VET = {
                             "VISITS": "VETERINARY_VISITS",
                             "PATIENTS": "VETERINARY_PATIENTS",
                             "VETERINARY_ASSISTANT": "VETERINARY_VITALS",
                             "DOCTOR_STATION": "VETERINARY_DOCTOR",
                             "PHARMACY": "VETERINARY_PHARMACY",
                             "PHARMACY_STORE": "VETERINARY_PHARMACY_STORE",
                             "LABS": "VETERINARY_LABS",
                             "SCHEDULE": "VETERINARY_SCHEDULE",
                             "ONLINE_CONSULT": "VETERINARY_ONLINE_CONSULT",
                             "OFFLINE_VISITS": "VETERINARY_OFFLINE_VISIT",
                             "MEDICINE_REMINDERS": "VETERINARY_MEDICINE_REMINDERS",
                             "CLINIC_SETTINGS": "VETERINARY_ADMIN_SETTINGS",
                             "METADATA_MANAGEMENT": "VETERINARY_METADATA",
                        }
                        bridge_key = EXT_TO_VET.get(cat_key, f"VETERINARY_{cat_key}")
                        matched_perms += [f"{bridge_key}_VIEW", f"{bridge_key}_CREATE", f"{bridge_key}_EDIT", f"{bridge_key}_DELETE"]
                    
                    has_view = any(p in flat_perms for p in matched_perms if p.endswith("_VIEW"))
                    has_create = any(p in flat_perms for p in matched_perms if p.endswith("_CREATE"))
                    has_edit = any(p in flat_perms for p in matched_perms if p.endswith("_EDIT"))
                    has_delete = any(p in flat_perms for p in matched_perms if p.endswith("_DELETE"))
                    
                    if has_view or has_create or has_edit or has_delete:
                        print(f"            ✅ Category MATCH - Including")
                        rebuilt_category = category.copy()
                        rebuilt_category['can_view'] = has_view
                        rebuilt_category['can_create'] = has_create
                        rebuilt_category['can_edit'] = has_edit
                        rebuilt_category['can_delete'] = has_delete
                        filtered_categories.append(rebuilt_category)
                        
                        # AGGREGATE to Service Level
                        if has_view: svc_can_view = True
                        if has_create: svc_can_create = True
                        if has_edit: svc_can_edit = True
                        if has_delete: svc_can_delete = True
                    else:
                        print(f"            ❌ Category NO MATCH - Excluding")
                else:
                    print(f"            ⚠️ No category_key — Excluding")
            
            # Include this service only if employee has any access
            if svc_can_view or svc_can_create or svc_can_edit or svc_can_delete or filtered_categories:
                print(f"      ➕ Adding service with {len(filtered_categories)} filtered categories")
                filtered_service = service.copy()
                filtered_service['categories'] = filtered_categories
                
                # Set aggregated permissions
                filtered_service['can_view'] = svc_can_view
                filtered_service['can_create'] = svc_can_create
                filtered_service['can_edit'] = svc_can_edit
                filtered_service['can_delete'] = svc_can_delete
                
                # Normalize service_key to VETERINARY_CORE if applicable
                if service_key != resolved_key:
                    filtered_service['service_key'] = resolved_key
                filtered_permissions.append(filtered_service)
            else:
                print(f"      ⏭️ SKIPPING - No access at service or category level")
        
        permissions_list = filtered_permissions
        print(f"   Tree size after filter: {len(permissions_list)}")
        print(f"{'='*100}\n")
        
    except OrganizationEmployee.DoesNotExist:
        # CASE B: Provider (Org or Individual)
        # Access = Purchased Plan (Upper Bound)
        # We do NOT intersect with "role defaults" anymore.
        
        print(f"\n{'='*100}")
        print(f"🏢 PROVIDER PERMISSION CALCULATION: {user.email}")
        print(f"{'='*100}")
        
        user_caps = user.get_all_plan_capabilities()
        # Note: VETERINARY_CORE is auto-added in get_all_plan_capabilities() if vet services exist
        
        print(f"   📊 Plan Capabilities Count: {len(user_caps)}")
        print(f"   📋 Plan Capabilities: {list(user_caps)}")
        print(f"{'='*100}\n")

    # Load service metadata dynamically from database (100% Database-Driven)
    # This replaces the old hardcoded simple_services dictionary
    
    # CRITICAL FIX: Only inject AllowedService for PROVIDERS, not employees
    # Employees already have their filtered tree from the try block above
    try:
        OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        is_employee = True
    except OrganizationEmployee.DoesNotExist:
        is_employee = False
    
    if not is_employee:
        # PROVIDER PATH: Add simple services from AllowedService
        allowed_services = AllowedService.objects.filter(verified_user=subscription_owner)
        
        
        print(f"\\n🔍 ALLOWED SERVICE INJECTION (PROVIDER ONLY)")
        print(f"   User Caps: {list(user_caps)}")
        print(f"   Allowed Services Count: {allowed_services.count()}")
    
        for allowed_svc in allowed_services:
            # Get the capability key from the service
            # For dynamic services, this comes from Service.category_key
            # Standardizing to match _build_permission_tree: UPPER and with underscores
            cap_key = allowed_svc.name.upper().replace(" ", "_").replace("&", "")
            svc_id_str = str(allowed_svc.service_id)
            
            print(f"       Checking: {allowed_svc.name} → {cap_key}")
            
            # Check if user has this capability
            if cap_key in user_caps or (cap_key == "VETERINARY" and "VETERINARY_CORE" in user_caps):
                print(f"          ✅ MATCH! Adding to tree")
                # Skip VETERINARY if we already have a real Veterinary service from a plan
                if (cap_key == "VETERINARY" or cap_key == "VETERINARY_CORE") and any("VETERINARY" in (p.get("service_key") or "").upper() for p in permissions_list):
                    print(f"          ⏭️ Skipping (already have VETERINARY service)")
                    continue

                # Check if already present to avoid duplicates (Check both ID and Key)
                exists = any(
                    p.get('service_key') == cap_key or p.get('service_id') == svc_id_str 
                    for p in permissions_list
                )

                if not exists:
                    permissions_list.append({
                        "service_id": svc_id_str,
                        "service_name": allowed_svc.name,
                        "service_key": cap_key,
                        "icon": allowed_svc.icon or "tabler-box",
                        "categories": [],
                        "can_view": True,
                        "can_create": True,
                        "can_edit": True,
                        "can_delete": True
                    })
                    print(f"          ➕ Added to permissions_list")
                else:
                    print(f"          ⏭️ Already in list (ID or Key match)")
            else:
                print(f"          ❌ NO MATCH (not in user_caps)")
    
        print(f"   Final Tree Count: {len(permissions_list)}\n")
    else:
        print(f"\n⏭️ SKIPPING ALLOWED SERVICE INJECTION (Employee - already filtered)\n")

    # -----------------------------------------
    # Construct plan_data from valid_sub
    # -----------------------------------------
    plan_data = None
    if valid_sub:
        plan_data = {
            "title": valid_sub.plan_title,
            "plan_title": valid_sub.plan_title,
            "subtitle": f"{valid_sub.billing_cycle_name} Plan",
            "billing_cycle_name": valid_sub.billing_cycle_name,
            "start_date": valid_sub.start_date,
            "end_date": valid_sub.end_date,
            "days_left": getattr(valid_sub, 'days_left', None),
            "is_expiring_soon": getattr(valid_sub, 'is_expiring_soon', False),
            "price_amount": getattr(valid_sub, 'price_amount', None),
            "price_currency": getattr(valid_sub, 'price_currency', 'INR'),
        }

    # -----------------------------------------
    # MANDATORY FILTERING FOR INDIVIDUAL PROVIDERS
    # Removes Management/Clinics/Employee/Role modules for solo practitioners
    # -----------------------------------------
    if subscription_owner.role and subscription_owner.role.upper() == 'INDIVIDUAL':
        print(f"🕵️  [FINAL FILTER] Stripping management modules for individual provider...")
        final_filtered_tree = []
        FORBIDDEN_KEYS = ['SYSTEM_ADMIN_CORE', 'ROLE_MANAGEMENT', 'EMPLOYEE_MANAGEMENT', 'CLINIC_MANAGEMENT']
        FORBIDDEN_NAMES = ['clinics', 'role management', 'employee management', 'system management', 'management']

        for svc in permissions_list:
            s_key = (svc.get('service_key') or "").upper()
            s_name = (svc.get('service_name') or "").lower()

            if s_key == 'SYSTEM_ADMIN_CORE' or s_name in FORBIDDEN_NAMES:
                continue

            svc_cats = svc.get('categories', [])
            if isinstance(svc_cats, dict):
                filtered_cats = {k: v for k, v in svc_cats.items() if (v.get('category_key') or "").upper() not in FORBIDDEN_KEYS and (v.get('name') or "").lower() not in FORBIDDEN_NAMES}
            else:
                filtered_cats = [c for c in svc_cats if (c.get('category_key') or "").upper() not in FORBIDDEN_KEYS and (c.get('name') or "").lower() not in FORBIDDEN_NAMES]

            if filtered_cats or s_key == 'VETERINARY_CORE':
                svc['categories'] = filtered_cats
                final_filtered_tree.append(svc)

        permissions_list = final_filtered_tree

    # -----------------------------------------
    # [NEW] VETERINARY HUB INJECTION & NORMALIZATION
    # -----------------------------------------
    if not is_employee:
        CLINICAL_MODULE_KEYS = {
            'PHARMACY', 'VISITS', 'LABS', 'DOCTOR_STATION', 'VETERINARY_ASSISTANT',
            'PATIENTS', 'OFFLINE_VISITS', 'MEDICINE_REMINDERS', 'CLINIC_SETTINGS',
            'METADATA_MANAGEMENT', 'BOARDING_BASIC', 'VETERINARY_CORE',
        }
        
        # 1. Normalize existing VETERINARY services to VETERINARY_CORE for frontend consistency
        has_vet_hub = False
        for svc in permissions_list:
            s_key = (svc.get('service_key') or '').upper()
            if s_key in ('VETERINARY', 'VETERINARY_CORE'):
                svc['service_key'] = 'VETERINARY_CORE'
                has_vet_hub = True

        # 2. Collect all category_keys currently in the tree
        existing_cat_keys = set()
        for svc in permissions_list:
            for cat in svc.get('categories', []):
                ck = (cat.get('category_key') or cat.get('name', '')).upper()
                existing_cat_keys.add(ck)

        has_clinical_cats = bool(existing_cat_keys & CLINICAL_MODULE_KEYS)

        # 3. If we have clinical modules but no VETERINARY_CORE node, inject it
        if has_clinical_cats and not has_vet_hub:
            print(f"🩺 [SIDEBAR FIX] Injecting VETERINARY_CORE service node (clinical modules detected)")
            vet_categories = []
            for svc in permissions_list:
                for cat in svc.get('categories', []):
                    ck = (cat.get('category_key') or cat.get('name', '')).upper()
                    if ck in CLINICAL_MODULE_KEYS:
                        vet_categories.append(cat)

            permissions_list.insert(0, {
                "service_id": "veterinary-core-injected",
                "service_name": "Veterinary Management",
                "service_key": "VETERINARY_CORE",
                "icon": "tabler-building-hospital",
                "can_view": True,
                "can_create": True,
                "can_edit": True,
                "can_delete": True,
                "categories": vet_categories,
            })
            has_vet_hub = True

    # -----------------------------------------
    # [NEW] CORE ADMINISTRATIVE MODULES INJECTION
    # Ensures Home, Marketplace, and Subscription are always in the tree if authorized.
    # -----------------------------------------
    CORE_MODULES = [
        ("ADMIN_CORE_HOME", "Home", "tabler-smart-home"),
        ("ADMIN_CORE_MARKETPLACE", "Marketplace Profile", "tabler-building-store"),
        ("ADMIN_CORE_SUBSCRIPTION", "My Subscription", "tabler-crown"),
    ]
    
    for cap_key, display_name, icon in CORE_MODULES:
        # Check if the user has either the base key or the VIEW variant
        is_authorized = cap_key in user_perms_set or f"{cap_key}_VIEW" in user_perms_set
        
        if is_authorized:
            # Avoid duplication
            if not any(p.get('service_key') == cap_key for p in permissions_list):
                 permissions_list.insert(0, {
                    "service_id": cap_key,
                    "service_name": display_name,
                    "service_key": cap_key,
                    "icon": icon,
                    "categories": [],
                    "can_view": True,
                    "can_create": True,
                    "can_edit": True,
                    "can_delete": True
                })

    response_data = {
        "permissions": permissions_list,
        "dynamic_capabilities": list(user_perms_set), # [NEW] Flat list for frontend stores
        "plan": plan_data,
        "user_profile": user_profile
    }

    return Response(response_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_provider_role_templates(request):
    """
    Returns standard role templates and feature definitions.
    """
    try:
        from .role_templates import get_role_templates
        data = get_role_templates()
        return Response(data)
    except Exception as e:
        import traceback
        print(f"Error fetching role templates: {e}")
        return Response({"error": str(e), "trace": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_allowed_services(request):
    """
    GET /api/provider/allowed-services/
    Returns list of services the provider can access.
    """
    try:
        verified_user = request.user
        print(f"DEBUG: get_allowed_services user={verified_user.email} (ID: {verified_user.auth_user_id})")
        
        # 1. Get services from Capabilities (Plan-based)
        capability_service_ids = set()
        if hasattr(verified_user, 'capabilities'):
            capability_service_ids = set(verified_user.capabilities.values_list('service_id', flat=True).distinct())
        
        # 2. Get services from AllowedService (Direct assignment)
        allowed_service_ids = set(AllowedService.objects.filter(verified_user=verified_user).values_list('service_id', flat=True))
        
        # Merge all IDs
        all_service_ids = capability_service_ids.union(allowed_service_ids)
        print(f"DEBUG: Found service_ids: {list(all_service_ids)}")
        
        # Fetch details from templates
        services = ProviderTemplateService.objects.filter(super_admin_service_id__in=all_service_ids)
        
        data = [
            {
                "service_id": s.super_admin_service_id,
                "name": s.name,
                "display_name": s.display_name,
                "icon": s.icon
            }
            for s in services
        ]
        
        return Response(data)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({"error": str(e), "trace": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from rest_framework import viewsets
from rest_framework.decorators import action
    # These are already imported at the top of the file
from .permissions import IsOrganizationAdmin, HasGranularCapability, require_granular_capability

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    Manage employees for the logged-in organization.
    """
    permission_classes = [IsAuthenticated, require_granular_capability('EMPLOYEE_MANAGEMENT')]
    serializer_class = OrganizationEmployeeSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='public_list')
    def public_list(self, request):
        """
        Minimalist list of employees for non-admin users (e.g. for doctor selection).
        Accessible to any authenticated staff member in the same organization.
        """
        qs = self.get_queryset()
        serializer = MinimalEmployeeSerializer(qs, many=True)
        return Response(serializer.data)
    
    def get_queryset(self):
        # Return employees where organization owner is the logged-in user
        user = self.request.user
        
        with open("debug_views.log", "a") as f:
            f.write(f"\\n[{timezone.now()}] Request User: {user} (ID: {user.id}) Role: {getattr(user, 'role', 'N/A')}\\n")
        
        # Find the ServiceProvider associated with the logged-in user
        try:
            # [FIX] Logic for employees to see their own org members
            emp_record = OrganizationEmployee.objects.filter(auth_user_id=user.auth_user_id).first()
            if emp_record:
                 provider = emp_record.organization
                 with open("debug_views.log", "a") as f:
                    f.write(f"[{timezone.now()}] User is employee. Org: {provider.id}\n")
            else:
                 provider = ServiceProvider.objects.get(verified_user=user)
                 with open("debug_views.log", "a") as f:
                    f.write(f"[{timezone.now()}] Found Provider Owner: {provider.id}\n")
            
            qs = OrganizationEmployee.objects.filter(organization=provider, deleted_at__isnull=True)
            
            with open("debug_views.log", "a") as f:
                f.write(f"[{timezone.now()}] Employee Count: {qs.count()}\\n")
                for emp in qs:
                    f.write(f"   - {emp.full_name} ({emp.role})\\n")
            
            return qs
        except ServiceProvider.DoesNotExist:
            with open("debug_views.log", "a") as f:
                f.write(f"[{timezone.now()}] ServiceProvider NOT found for user {user.id}\\n")
            return OrganizationEmployee.objects.none()
        except Exception as e:
            with open("debug_views.log", "a") as f:
                f.write(f"[{timezone.now()}] Error in get_queryset: {e}\n")
            return OrganizationEmployee.objects.none()

    @action(detail=False, methods=['get'], url_path='details/(?P<auth_user_id>[^/.]+)')
    def details_by_auth_id(self, request, auth_user_id=None):
        """
        Fetch detailed employee info (for Super Admin popup).
        Rich metadata including Organization and Capabilities.
        """
        try:
            employee = OrganizationEmployee.objects.select_related('organization__verified_user', 'provider_role').get(auth_user_id=auth_user_id)
            serializer = self.get_serializer(employee)
            return Response(serializer.data)
        except OrganizationEmployee.DoesNotExist:
            return Response({
                "error": "Employee record not found",
                "auth_user_id": auth_user_id,
                "hint": "Ensure the user is correctly registered in the Service Provider service."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in details_by_auth_id: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """
        Proxy staff creation to Auth Service, then DIRECTLY create OrganizationEmployee.
        Does NOT rely on Kafka to avoid race conditions and silent failures.
        """
        user = request.user

        # 1. Build registration payload
        # Staff always have "employee" type in Auth Service.
        # Specific job roles are managed via provider_role.
        auth_data = {
            "full_name": request.data.get("full_name"),
            "email": request.data.get("email"),
            "phone_number": request.data.get("phone_number"),
            "role": "5",  # Force system role to employee (ID 5 in Auth Service) - USING STRING TO PREVENT CRASH
            "organization_id": str(user.auth_user_id),
            "provider_role": request.data.get("provider_role"),
        }

        # 2. Call Auth Service to register the user
        auth_header = request.headers.get('Authorization')
        print(f"DEBUG: Creating employee. Auth data: {auth_data}")
        try:
            auth_url = "http://localhost:8000/auth/api/auth/register/"
            response = requests.post(
                auth_url,
                json=auth_data,
                headers={"Authorization": auth_header}
            )
            print(f"DEBUG: Auth Service response status={response.status_code}, body={response.text}")
            if response.status_code != 201:
                return Response(response.json(), status=response.status_code)

        except Exception as e:
            return Response({"error": f"Failed to connect to Auth Service: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. [DIRECT CREATION] Get the organization's ServiceProvider record
        try:
            org_provider = ServiceProvider.objects.get(verified_user=user)
        except ServiceProvider.DoesNotExist:
            # Fallback: auto-create ServiceProvider for this org user
            org_provider, _ = ServiceProvider.objects.get_or_create(
                verified_user=user,
                defaults={"provider_type": "ORGANIZATION"}
            )

        # 4. Get or create the employee's VerifiedUser record (Kafka will update it later too)
        emp_auth_user_id = response.json().get("auth_user_id") or response.json().get("user_id")
        
        if emp_auth_user_id:
            emp_verified_user, _ = VerifiedUser.objects.get_or_create(
                auth_user_id=emp_auth_user_id,
                defaults={
                    "full_name": auth_data["full_name"],
                    "email": auth_data["email"],
                    "phone_number": auth_data["phone_number"],
                    "role": auth_data["role"],
                }
            )
            
            # 5. Resolve provider_role if given
            provider_role = None
            provider_role_id = request.data.get("provider_role")
            if provider_role_id:
                try:
                    provider_role = ProviderRole.objects.get(id=provider_role_id)
                except (ProviderRole.DoesNotExist, Exception):
                    pass

            # 6. Create the OrganizationEmployee record directly
            emp, created = OrganizationEmployee.objects.update_or_create(
                auth_user_id=emp_auth_user_id,
                defaults={
                    "organization": org_provider,
                    "full_name": auth_data["full_name"],
                    "email": auth_data["email"],
                    "phone_number": auth_data["phone_number"],
                    "role": auth_data["role"],
                    "provider_role": provider_role,
                    "status": "PENDING",
                    "joined_at": None, # Will be set when they accept invite/activate
                    "created_by": str(user.auth_user_id),  # FIX: NOT NULL constraint
                    "average_rating": 0.0,
                    "total_ratings": 0,
                }
            )
            logger.info(f"✅ Directly created OrganizationEmployee {emp_auth_user_id} for org {user.auth_user_id}")
            
            # Sync to Kafka immediately so permissions propagate to other services
            from .kafka_producer import publish_employee_updated
            publish_employee_updated(emp)
            
        else:
            logger.warning("⚠️ Auth Service did not return auth_user_id — employee record not created directly")

        return Response(response.json(), status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        employee = self.get_object()
        employee.status = 'DISABLED'
        employee.save()
        
        # 🛡️ Audit Log
        PermissionAuditLog.log_action(
            actor=request.user,
            action='EMPLOYEE_SUSPENDED',
            target_employee=employee,
            details={'status': 'DISABLED'},
            request=request
        )

        # Sync with Auth Service (optional, but good practice)
        from .kafka_producer import publish_employee_updated
        publish_employee_updated(employee)
        
        return Response({'status': 'DISABLED'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        employee = self.get_object()
        employee.status = 'ACTIVE'
        employee.save()
        
        # 🛡️ Audit Log
        PermissionAuditLog.log_action(
            actor=request.user,
            action='EMPLOYEE_ACTIVATED',
            target_employee=employee,
            details={'status': 'ACTIVE'},
            request=request
        )

        # Sync with Auth Service
        from .kafka_producer import publish_employee_updated
        publish_employee_updated(employee)
        
        return Response({'status': 'ACTIVE'})

    def perform_destroy(self, instance):
        auth_user_id = instance.auth_user_id
        instance.deleted_at = timezone.now()
        instance.save()
        
        # Sync with Auth Service
        from .kafka_producer import publish_employee_deleted
        publish_employee_deleted(auth_user_id)

    def perform_update(self, serializer):
        old_employee = self.get_object()
        old_role = old_employee.provider_role.name if old_employee.provider_role else None
        
        employee = serializer.save()
        new_role = employee.provider_role.name if employee.provider_role else None
        
        # 🛡️ Audit Log if role changed
        if old_role != new_role:
            PermissionAuditLog.log_action(
                actor=self.request.user,
                action='ROLE_ASSIGNED',
                target_employee=employee,
                details={
                    'old_role': old_role,
                    'new_role': new_role
                },
                request=self.request
            )

        # Sync with Auth Service
        from .kafka_producer import publish_employee_updated
        publish_employee_updated(employee)

from .models import AllowedService



class PublicProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public Marketplace API for Pet Parents.
    Grants access to list and view active providers.
    """
    permission_classes = [AllowAny] 
    queryset = ServiceProvider.objects.filter(profile_status='active', is_fully_verified=True)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PublicProviderDetailSerializer
        return PublicProviderSerializer
    def get_queryset(self):
         # Allow filtering by Query Params
         qs = super().get_queryset()
         
         # Filter by type (Individual vs Organization)
         provider_type = self.request.query_params.get('type')
         if provider_type:
             qs = qs.filter(verified_user__role__iexact=provider_type)
             
         # Search by Name or City
         search = self.request.query_params.get('search')
         if search:
             from django.db.models import Q
             qs = qs.filter(
                 Q(verified_user__full_name__icontains=search) | 
                 Q(verified_user__billing_profile__company_name__icontains=search) |
                 Q(verified_user__billing_profile__contact__icontains=search)
             )
             
         return qs

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        GET /api/provider/public-providers/active/
        Discovery Marketplace API for Pet Parents.
        Returns: LightDTO with active plan providers.
        """
        from .services import ProviderService
        from .serializers import ActiveProviderDTO
        
        # Following Clean Architecture (ViewSet -> Service -> Repository)
        providers = ProviderService.list_active_providers()
        
        # Search / Filter support
        search = request.query_params.get('search')
        if search:
             from django.db.models import Q
             providers = providers.filter(
                 Q(verified_user__full_name__icontains=search) | 
                 Q(verified_user__billing_profile__company_name__icontains=search) |
                 Q(verified_user__billing_profile__contact__icontains=search)
             )

        # Pagination
        page = self.paginate_queryset(providers)
        if page is not None:
            serializer = ActiveProviderDTO(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            
        serializer = ActiveProviderDTO(providers, many=True, context={'request': request})
        return Response(serializer.data)


class EmployeeAssignmentViewSet(viewsets.ViewSet):
    """
    Manage service assignments for employees.
    Supports granular permissions (Service -> Category -> Facility).
    """
    permission_classes = [IsAuthenticated, require_granular_capability('EMPLOYEE_MANAGEMENT')]

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        List services available to the Organization (logged-in user).
        GET /api/provider/employee-assignments/available/
        """
        user = request.user
        data = _build_permission_tree(user)
        return Response(data)

    @action(detail=True, methods=['get'])
    def assigned(self, request, pk=None):
        """
        List services currently assigned to the employee.
        GET /api/provider/employee-assignments/{pk}/assigned/
        """
        # Verify employee belongs to org
        try:
            provider = ServiceProvider.objects.get(verified_user=request.user)
            employee = OrganizationEmployee.objects.get(id=pk, organization=provider)
        except (ServiceProvider.DoesNotExist, OrganizationEmployee.DoesNotExist):
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            emp_user = VerifiedUser.objects.get(auth_user_id=employee.auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response([])

        data = _build_permission_tree(emp_user)
        return Response(data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Assign granular permissions to an employee.
        POST /api/provider/employee-assignments/{pk}/assign/
        Body: { 
            "permissions": [
                { "service_id": "...", "category_id": "...", "facility_id": "...", "can_view": true, ... }
            ] 
        }
        """
        permissions_data = request.data.get('permissions', [])
        
        try:
            provider = ServiceProvider.objects.get(verified_user=request.user)
        except (ServiceProvider.DoesNotExist, ValueError):
            return Response({"error": "Provider not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            employee = OrganizationEmployee.objects.get(id=pk, organization=provider)
        except OrganizationEmployee.DoesNotExist:
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            emp_user = VerifiedUser.objects.get(auth_user_id=employee.auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "Employee user record not found"}, status=status.HTTP_404_NOT_FOUND)

        # 1. Clear existing capabilities for this employee
        # We only clear "EMPLOYEE_ASSIGNMENT" plan_id to avoid messing with other potential system permissions
        # But for now, let's assume all capabilities for an employee are assignments.
        ProviderCapabilityAccess.objects.filter(user=emp_user).delete()
        
        # 2. Clear AllowedService (we will rebuild it)
        AllowedService.objects.filter(verified_user=emp_user).delete()

        # 3. Create new capabilities
        created_count = 0
        assigned_service_ids = set()

        # Pre-fetch templates for AllowedService creation
        service_ids_to_fetch = set(p.get('service_id') for p in permissions_data if p.get('service_id'))
        templates = ProviderTemplateService.objects.filter(super_admin_service_id__in=service_ids_to_fetch)
        template_map = {t.super_admin_service_id: t for t in templates}

        for perm in permissions_data:
            service_id = perm.get('service_id')
            if not service_id:
                continue
                
            # Security Check: Does Org have this permission?
            # For MVP, we'll skip complex validation and trust the frontend (Org can only see what they have).
            # In production, we should query Org's capabilities here.

            ProviderCapabilityAccess.objects.create(
                user=emp_user,
                plan_id="EMPLOYEE_ASSIGNMENT",
                service_id=service_id,
                category_id=perm.get('category_id'),
                facility_id=perm.get('facility_id'),
                pricing_id=perm.get('pricing_id'),
                can_view=perm.get('can_view', False),
                can_create=perm.get('can_create', False),
                can_edit=perm.get('can_edit', False),
                can_delete=perm.get('can_delete', False)
            )
            created_count += 1
            assigned_service_ids.add(service_id)

        # 4. Rebuild AllowedService (High-level access)
        for sid in assigned_service_ids:
            tmpl = template_map.get(sid)
            if tmpl:
                AllowedService.objects.create(
                    verified_user=emp_user,
                    service_id=sid,
                    name=tmpl.display_name,
                    icon=tmpl.icon
                )
            else:
                print(f"⚠️ Warning: Template not found for service {sid} during assignment for {emp_user.email}")
        
        # 🛡️ Audit Log
        PermissionAuditLog.log_action(
            actor=request.user,
            action='PERMISSIONS_ASSIGNED',
            target_employee=employee,
            details={'permission_count': created_count},
            request=request
        )

        # 🔄 Invalidate Cache
        employee.invalidate_permission_cache()

        return Response({"status": "updated", "permissions_count": created_count})
class CapabilityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List all available capabilities with human-readable labels.
    """
    queryset = Capability.objects.all()
    serializer_class = CapabilitySerializer
    permission_classes = [IsAuthenticated]


class ProviderRoleViewSet(viewsets.ModelViewSet):
    """
    Manage provider-scoped roles.
    """
    serializer_class = ProviderRoleSerializer
    permission_classes = [IsAuthenticated, require_granular_capability('ROLE_MANAGEMENT')]

    def get_queryset(self):
        try:
            provider = ServiceProvider.objects.get(verified_user=self.request.user)
            return ProviderRole.objects.filter(provider=provider)
        except (ServiceProvider.DoesNotExist, ValueError):
            return ProviderRole.objects.none()

    def perform_create(self, serializer):
        try:
            provider = ServiceProvider.objects.get(verified_user=self.request.user)
        except (ServiceProvider.DoesNotExist, ValueError):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Provider profile not found.")

        from django.db import IntegrityError
        from rest_framework.exceptions import ValidationError
        try:
            role = serializer.save(provider=provider)
        except IntegrityError:
            raise ValidationError({"name": ["A role with this name already exists for your organization."]})
        
        # 🛡️ Audit Log (Guard against TransientUser in actor)
        actor = self.request.user if isinstance(self.request.user, VerifiedUser) else None
        
        PermissionAuditLog.log_action(
            actor=actor,
            action='ROLE_CREATED',
            target_role=role,
            details={
                'name': role.name,
                'description': role.description,
                'actor_info': str(self.request.user)
            },
            request=self.request
        )

    def perform_update(self, serializer):
        from django.db import IntegrityError
        from rest_framework.exceptions import ValidationError
        
        try:
            role = serializer.save()
        except IntegrityError as e:
            if 'name' in str(e).lower() or 'unique' in str(e).lower():
                raise ValidationError({"name": ["A role with this name already exists for your organization."]})
            raise  # Re-raise if it's some other IntegrityError causing failure (e.g. duplicate child keys)
        
        # 🛡️ Audit Log (Guard against TransientUser)
        actor = self.request.user if isinstance(self.request.user, VerifiedUser) else None
        
        PermissionAuditLog.log_action(
            actor=actor,
            action='ROLE_UPDATED',
            target_role=role,
            details={
                'name': role.name,
                'description': role.description,
                'actor_info': str(self.request.user)
            },
            request=self.request
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        role_name = instance.name
        role_id = instance.id
        logger.info(f"🗑️ Attempting to delete ProviderRole: {role_name} ({role_id})")
        
        # 🛡️ Audit Log (Guard against TransientUser)
        actor = self.request.user if isinstance(self.request.user, VerifiedUser) else None
        
        PermissionAuditLog.log_action(
            actor=actor,
            action='ROLE_DELETED',
            target_role=None, # Role is about to be deleted
            details={
                'name': role_name,
                'id': str(role_id),
                'actor_info': str(self.request.user)
            },
            request=self.request
        )
        
        # 1. Explicit Model-based Cleanup of Capabilities
        # Note: CASCADE will do this too, but we do it manually for logging/clarity
        caps_qs = ProviderRoleCapability.objects.filter(provider_role=instance)
        caps_count = caps_qs.count()
        caps_qs.delete()
        logger.info(f"   ↳ Deleted {caps_count} capabilities (via explicit filter).")
        
        # 2. Explicit Model-based Cleanup of Employees
        emps_qs = OrganizationEmployee.objects.filter(provider_role=instance)
        emps_count = emps_qs.count()
        emps_qs.update(provider_role=None)
        logger.info(f"   ↳ Unlinked role from {emps_count} employees (via explicit filter).")
        
        # 3. Delete the role
        instance.delete()
        logger.info(f"✅ Successfully deleted ProviderRole: {role_name}")


class ConsultationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationType
        fields = ['id', 'name', 'description', 'duration_minutes', 'consultation_fee', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConsultationTypeViewSet(viewsets.ModelViewSet):
    """
    Provider manages their consultation types.
    Pet owners can GET /api/provider/consultation-types/?provider_id=<id>
    """
    serializer_class = ConsultationTypeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAuthenticated(), require_granular_capability('CLINIC_MANAGEMENT')()]

    def get_queryset(self):
        # Public read: filter by provider_id query param
        provider_id_param = self.request.query_params.get('provider_id')
        if provider_id_param:
            return ConsultationType.objects.filter(
                provider_id=provider_id_param, is_active=True
            )
        # Authenticated provider: return own types
        try:
            provider = ServiceProvider.objects.get(verified_user=self.request.user)
            return ConsultationType.objects.filter(provider=provider)
        except (ServiceProvider.DoesNotExist, AttributeError):
            return ConsultationType.objects.none()

    def perform_create(self, serializer):
        provider = ServiceProvider.objects.get(verified_user=self.request.user)
        serializer.save(provider=provider)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_access(request):
    """
    Returns allowed modules for the dynamic sidebar.
    GET /api/provider/permissions/my-access/
    """
    user = request.user
    
    # 1. Get Effective Capability Keys
    raw_keys = set()
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        # Employees: use their role-gated permissions (already fully granular with _VIEW etc.)
        raw_keys = set(emp.get_final_permissions())
    except OrganizationEmployee.DoesNotExist:
        # Organization/Individual Owner: use the full plan-derived capabilities
        # get_all_plan_capabilities() correctly expands plan categories into all
        # VETERINARY_*, BOARDING_*, GROOMING_* etc. keys with _VIEW/_CREATE/_EDIT/_DELETE suffixes
        raw_keys = user.get_all_plan_capabilities()
    
    # 2. Derive base keys for Module lookup
    capability_keys = set()
    for key in raw_keys:
        base_key = key
        for sfx in ["_VIEW", "_CREATE", "_EDIT", "_DELETE"]:
            if key.endswith(sfx):
                base_key = key[:-len(sfx)]
                break
        capability_keys.add(base_key)

    # [BRIDGE] Expand granular keys to legacy FeatureModule keys
    # This ensures modern employee roles correctly trigger the sidebar modules.
    VET_MAP = {
        "VETERINARY_VISITS": "VISITS",
        "VETERINARY_PATIENTS": "PATIENTS",
        "VETERINARY_VITALS": ["VITALS", "VETERINARY_ASSISTANT"],
        "VETERINARY_DOCTOR": "DOCTOR_STATION",
        "VETERINARY_PHARMACY": "PHARMACY",
        "VETERINARY_PHARMACY_STORE": "PHARMACY_STORE",
        "VETERINARY_LABS": "LABS",
        "VETERINARY_SCHEDULE": "SCHEDULE",
        "VETERINARY_OFFLINE_VISIT": "OFFLINE_VISITS",
        "VETERINARY_ONLINE_CONSULT": "ONLINE_CONSULT",
        "VETERINARY_MEDICINE_REMINDERS": "MEDICINE_REMINDERS",
        "VETERINARY_CORE": ["VETERINARY-MANAGEMENT", "VETERINARY"],
    }
    
    extra_keys = set()
    for k in capability_keys:
        if k in VET_MAP:
            mapped = VET_MAP[k]
            if isinstance(mapped, list):
                extra_keys.update(mapped)
            else:
                extra_keys.add(mapped)
    capability_keys.update(extra_keys)
        
    # 2. Fetch Modules for these keys
    from .models import FeatureModule
    modules = FeatureModule.objects.filter(capability__key__in=capability_keys, is_active=True).values(
        'name', 'route', 'icon', 'sequence', 'key'
    ).order_by('sequence')
    
    return Response({
        "capabilities": list(raw_keys),
        "modules": list(modules)
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_dashboard_summary(request):
    """
    Returns high-level analytics for the provider dashboard.
    """
    import requests
    user = request.user
    service_id = request.GET.get('service_id')
    
    try:
        # Find the ServiceProvider associated with the logged-in user
        provider = ServiceProvider.objects.get(verified_user__auth_user_id=user.auth_user_id)
        
        employee_count = OrganizationEmployee.objects.filter(organization=provider, deleted_at__isnull=True).count()
        role_count = ProviderRole.objects.filter(provider=provider).count()
        
        # Fetch Clinic count from Veterinary Service
        clinic_count = 0
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                # Internal URL for veterinary service (No 'api/' prefix in veterinary_service/urls.py)
                VET_SERVICE_URL = "http://127.0.0.1:8004/veterinary/clinics/"
                response = requests.get(
                    VET_SERVICE_URL, 
                    headers={"Authorization": auth_header},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    # ClinicViewSet returns a list or a paginated object
                    if isinstance(data, dict):
                         clinic_count = data.get('count', 0)
                    elif isinstance(data, list):
                         clinic_count = len(data)
        except Exception as e:
            logger.error(f"Error fetching clinic count from Veterinary Service: {e}")

        # Fetch Bookings Count from Customer Service
        booking_stats = {"total_bookings": 0, "pending_bookings": 0, "total_revenue": 0, "trend": []}
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                # Call the new stats endpoint
                STATS_URL = f"http://127.0.0.1:8005/api/pet-owner/bookings/bookings/stats/?provider_id={provider.id}"
                if service_id:
                    STATS_URL += f"&service_id={service_id}"
                
                response = requests.get(
                    STATS_URL, 
                    headers={"Authorization": auth_header},
                    timeout=5
                )
                if response.status_code == 200:
                    booking_stats = response.json()
        except Exception as e:
            logger.error(f"Error fetching booking stats from Customer Service: {e}")

        # Calculate Rating Distribution
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        try:
            from django.db.models import Count
            # provider.ratings is the related name
            dist_qs = provider.ratings.values('rating').annotate(count=Count('rating'))
            for item in dist_qs:
                r_val = item.get('rating')
                if r_val in rating_dist:
                    rating_dist[r_val] = item.get('count', 0)
        except Exception as e:
            logger.error(f"Error calculating rating distribution: {e}")

        return Response({
            "total_employees": employee_count,
            "total_roles": role_count,
            "total_clinics": clinic_count,
            "total_ratings": provider.total_ratings,
            "average_rating": provider.average_rating,
            "rating_distribution": rating_dist,
            "bookings": booking_stats, 
        })
        
    except ServiceProvider.DoesNotExist:
        return Response({"detail": "Service Provider profile not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Unexpected error in get_dashboard_summary: {e}")
        return Response({"error": str(e)}, status=500)

@api_view(["GET"])
@permission_classes([AllowAny]) 
def resolve_role_capabilities(request):
    """
    Internal endpoint for other services to resolve role names to capabilities.
    GET /api/provider/roles/resolve/?org_id=...&role_name=...
    """
    org_id = request.query_params.get('org_id')
    role_name = request.query_params.get('role_name')
    
    if not org_id or not role_name:
        return Response({"error": "Missing org_id or role_name"}, status=400)
    
    try:
        # Models already imported at top-level
        from .models import ProviderRoleCapability, VerifiedUser
        
        # 0. Special Handling for Organization Admin/Owner
        if role_name.lower() in ['admin', 'owner', 'organization', 'individual']:
            user = VerifiedUser.objects.filter(auth_user_id=org_id).first()
            if user:
                caps = list(user.get_all_plan_capabilities())
                # For Owners, we grant full CRUD on everything they own
                granular_caps = [{
                    "capability_key": cap,
                    "can_view": True, "can_create": True, "can_edit": True, "can_delete": True
                } for cap in caps]
                return Response({
                    "role": role_name, 
                    "capabilities": granular_caps, 
                    "flat_keys": caps,
                    "source": "organization_plan"
                })
        
        # 1. Check for Custom Provider Role
        role = ProviderRole.objects.filter(provider__verified_user__auth_user_id=org_id, name__iexact=role_name).first()
        if role:
            role_caps = ProviderRoleCapability.objects.filter(provider_role=role)
            granular_caps = []
            
            # Map flat keys back to base namespaces for legacy compat
            cap_map = {}
            flat_keys = [rc.permission_key for rc in role_caps]
            
            for key in flat_keys:
                base_key = key
                suffix = "VIEW"
                for sfx in ["_VIEW", "_CREATE", "_EDIT", "_DELETE"]:
                    if key.endswith(sfx):
                        base_key = key[:-len(sfx)]
                        suffix = sfx[1:]
                        break
                
                if base_key not in cap_map:
                    cap_map[base_key] = {"can_view": False, "can_create": False, "can_edit": False, "can_delete": False}
                    
                cap_map[base_key][f"can_{suffix.lower()}"] = True
            
            for b_key, flags in cap_map.items():
                granular_caps.append({
                    "capability_key": b_key,
                    "can_view": flags["can_view"],
                    "can_create": flags["can_create"],
                    "can_edit": flags["can_edit"],
                    "can_delete": flags["can_delete"]
                })
            
            # Always ensure VETERINARY_CORE if it has any VETERINARY_* caps
            # [NUCLEAR FILTER] Even if caps exist, strip them for Gold/Basic non-vet plans
            from provider_cart.models import PurchasedPlan
            # Resolve the account owner's plan for this org_id
            owner_plan = PurchasedPlan.objects.filter(verified_user__auth_user_id=org_id, is_active=True).first()
            p_title = (owner_plan.plan_title or "").lower() if owner_plan else ""
            is_p_vet = "veterinary" in p_title
            is_p_non_vet = ("gold" in p_title or "basic" in p_title) and not is_p_vet

            if is_p_non_vet:
                # Nuclear strip
                flat_keys = [k for k in flat_keys if not str(k).startswith("VETERINARY")]
                granular_caps = [c for c in granular_caps if not str(c.get("capability_key", "")).startswith("VETERINARY")]
            elif any(str(c).startswith('VETERINARY_') for c in flat_keys) and 'VETERINARY_CORE' not in flat_keys:
                granular_caps.append({
                    "capability_key": "VETERINARY_CORE",
                    "can_view": True, "can_create": True, "can_edit": True, "can_delete": True
                })
                flat_keys.append("VETERINARY_CORE")
                
            return Response({
                "role": role_name, 
                "capabilities": granular_caps, 
                "flat_keys": flat_keys,
                "source": "custom_role"
            })
            
        # 2. Fallback to Legacy Map (System Defaults)
        flat_keys = OrganizationEmployee.LEGACY_ROLE_MAP.get(role_name.lower(), [])
        if flat_keys:
             granular_caps = [{
                 "capability_key": cap,
                 "can_view": True, "can_create": True, "can_edit": True, "can_delete": True
             } for cap in flat_keys]
             return Response({
                 "role": role_name, 
                 "capabilities": granular_caps, 
                 "flat_keys": flat_keys,
                 "source": "legacy_map"
             })

        # [FIX] No capabilities for unknown roles. Never grant VETERINARY_CORE by default.
        return Response({
            "role": role_name, 
            "capabilities": [], 
            "flat_keys": [],
            "source": "fallback_empty"
        })
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)

class RatingSubmitView(APIView):
    """
    POST /api/provider/ratings/
    Submits a new rating and updates the provider's average_rating.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List all ratings for the authenticated provider, OR
        Return a specific rating if provider_id and service_id are provided.
        """
        # 1. Check if user is looking for their own rating of a specific service
        provider_id = request.query_params.get('provider_id')
        service_id = request.query_params.get('service_id')
        
        if provider_id and service_id:
            try:
                rating = ProviderRating.objects.get(
                    customer_id=request.user.auth_user_id,
                    provider_id=provider_id,
                    service_id=service_id
                )
                return Response(ProviderRatingSerializer(rating).data)
            except ProviderRating.DoesNotExist:
                return Response({"rating": 0, "review": ""}, status=200)

        # 2. Existing logic for providers (Owner or Organization for Employees)
        try:
            try:
                # Direct check (for Owners)
                provider = ServiceProvider.objects.get(verified_user__auth_user_id=request.user.auth_user_id)
            except ServiceProvider.DoesNotExist:
                # Employee check (find organization owner)
                emp = OrganizationEmployee.objects.get(auth_user_id=request.user.auth_user_id)
                provider = ServiceProvider.objects.get(verified_user=emp.organization.verified_user)

            ratings = ProviderRating.objects.filter(provider=provider)
            
            # Optional filter by employee
            employee_id = request.query_params.get('employee_id')
            if employee_id:
                ratings = ratings.filter(assigned_employee_id=employee_id)
                
            serializer = ProviderRatingSerializer(ratings, many=True)
            return Response(serializer.data)
        except ServiceProvider.DoesNotExist:
            return Response({"error": "Provider profile not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def patch(self, request):
        """
        Allows provider to respond to a rating.
        Expects: { "rating_id": "...", "response": "..." }
        """
        rating_id = request.data.get('rating_id')
        response_text = request.data.get('response')

        if not rating_id or not response_text:
            return Response({"error": "rating_id and response are required"}, status=400)

        try:
            # 1. Verify provider profile
            provider = ServiceProvider.objects.get(verified_user__auth_user_id=request.user.auth_user_id)
            
            # 2. Find and update the rating
            rating = get_object_or_404(ProviderRating, id=rating_id, provider=provider)
            
            rating.provider_response = response_text
            rating.responded_at = timezone.now()
            rating.save(update_fields=['provider_response', 'responded_at'])

            return Response({
                "message": "Response submitted successfully",
                "provider_response": rating.provider_response,
                "responded_at": rating.responded_at
            })

        except ServiceProvider.DoesNotExist:
            return Response({"error": "Provider profile not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def post(self, request):
        provider_id = request.data.get('provider_id')
        service_id = request.data.get('service_id')
        assigned_employee_id = request.data.get('assigned_employee_id')
        rating_val = request.data.get('rating')
        review_text = request.data.get('review')
        customer_id = request.user.auth_user_id

        if not provider_id or rating_val is None:
            return Response({"error": "provider_id and rating are required"}, status=400)

        try:
            rating_val = int(rating_val)
            if not (1 <= rating_val <= 5):
                raise ValueError()
        except ValueError:
            return Response({"error": "Rating must be between 1 and 5"}, status=400)

        provider = get_object_or_404(ServiceProvider, id=provider_id)

        # Security: Prevent self-rating
        if provider.verified_user.auth_user_id == customer_id:
            return Response({"error": "You cannot rate yourself"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            customer_name = getattr(request.user, 'full_name', None)
            customer_email = getattr(request.user, 'email', None)
            customer_role = getattr(request.user, 'role', None)

            # 1. Create the rating (or update if customer+provider+service unique)
            # Use update_or_create to handle re-submissions for the same service
            rating_obj, created = ProviderRating.objects.update_or_create(
                customer_id=customer_id,
                provider=provider,
                service_id=service_id,
                assigned_employee_id=assigned_employee_id,
                defaults={
                    "rating": rating_val,
                    "review": review_text,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_role": customer_role
                }
            )

            # 2. Recalculate Provider Totals
            # Instead of full aggregation, use the suggested running average formula
            # Note: If it's an update, the formula is slightly different, 
            # but for simplicity we'll just re-aggregate if it's not a lot of ratings,
            # OR just strictly follow the "new rating" logic for now as requested.
            # Realistically, if it's an update, we should subtract the old and add the new.
            
            # Simple aggregation is safer and still fast for typical provider rating counts
            from django.db.models import Avg, Count
            stats = ProviderRating.objects.filter(provider=provider).aggregate(
                avg=Avg('rating'),
                count=Count('id')
            )
            
            provider.average_rating = round(stats['avg'] or 0.0, 1)
            provider.total_ratings = stats['count'] or 0
            provider.save(update_fields=['average_rating', 'total_ratings'])

            # 3. Recalculate Employee Totals (if applicable)
            if assigned_employee_id:
                # OrganizationEmployee already imported at top-level
                # Use auth_user_id as assigned_employee_id (standard for our UUID refs)
                employee = OrganizationEmployee.objects.filter(auth_user_id=assigned_employee_id).first()
                if employee:
                    emp_stats = ProviderRating.objects.filter(assigned_employee_id=assigned_employee_id).aggregate(
                        avg=Avg('rating'),
                        count=Count('id')
                    )
                    employee.average_rating = round(emp_stats['avg'] or 0.0, 1)
                    employee.total_ratings = emp_stats['count'] or 0
                    employee.save(update_fields=['average_rating', 'total_ratings'])
            return Response({
                "message": "Rating submitted successfully",
                "average_rating": provider.average_rating,
                "total_ratings": provider.total_ratings
            }, status=status.HTTP_201_CREATED)


class PublicProviderRatingView(APIView):
    """
    GET: List all ratings for a specific provider (publicly).
    """
    permission_classes = [AllowAny]

    def get(self, request, provider_id):
        ratings = ProviderRating.objects.filter(provider_id=provider_id).order_by('-created_at')
        
        # Optional filter by employee
        employee_id = request.query_params.get('employee_id')
        if employee_id:
            ratings = ratings.filter(assigned_employee_id=employee_id)
            
        serializer = ProviderRatingSerializer(ratings, many=True)
        return Response(serializer.data)
@api_view(["GET"])
@permission_classes([AllowAny])
def resolve_booking_details(request):
    """
    Internal/Public API to resolve Service, Category, Facility names AND Price by IDs.
    Used by Booking service for snapshotting.
    """
    service_id = request.query_params.get('service_id')
    facility_id = request.query_params.get('facility_id')
    consultation_type_id = request.query_params.get('consultation_type_id')
    employee_id = request.query_params.get('employee_id')
    provider_id_param = request.query_params.get('provider_id')

    if not service_id or not facility_id:
        return Response({"error": "service_id and facility_id are required."}, status=status.HTTP_400_BAD_REQUEST)

    from provider_dynamic_fields.models import (
        ProviderFacility, ProviderCategory, ProviderPricing,
        ProviderTemplateFacility, ProviderTemplateService, ProviderTemplatePricing
    )
    from .models import ConsultationType, OrganizationEmployee

    facility = None
    category = None
    service = None
    provider_name = "Service Provider"
    price_snapshot = {}
    is_template = False

    # 1. Try resolving Custom Facility (Provider-Created)
    try:
        facility = ProviderFacility.objects.get(id=facility_id)
        category = facility.category
        # Note: Custom categories store service_id as a string (SuperAdmin ID)
        # We try to get the template service to get the display name
        try:
            service_obj = ProviderTemplateService.objects.get(super_admin_service_id=category.service_id)
            service_name = service_obj.display_name
        except ProviderTemplateService.DoesNotExist:
            service_name = category.service_id or "General Service"

        price_snapshot = {
            "price": str(facility.price),
            "billing_unit": "PER_SESSION", # Default for custom
            "duration_minutes": facility.duration_minutes,
            "protocol_type": facility.protocol_type,
            "pricing_strategy": facility.pricing_strategy,
        }
        
        # Check for explicit Pricing rules
        pricing = ProviderPricing.objects.filter(facility=facility, is_active=True).first()
        if pricing:
            price_snapshot.update({
                "price": str(pricing.price),
                "billing_unit": pricing.billing_unit,
                "duration_minutes": pricing.duration_minutes or facility.duration_minutes,
                "service_duration_type": pricing.service_duration_type,
                "pricing_model": pricing.pricing_model,
                "duration_value": pricing.duration_value,
            })

    except (ProviderFacility.DoesNotExist, ValueError, TypeError):
        # 2. Try resolving Template Facility (SuperAdmin)
        try:
            facility = ProviderTemplateFacility.objects.get(super_admin_facility_id=facility_id)
            category = facility.category
            service = category.service
            service_name = service.display_name
            is_template = True

            # Try to find the template price
            try:
                pricing = ProviderTemplatePricing.objects.filter(facility=facility).first()
                if pricing:
                    price_snapshot = {
                        "price": str(pricing.price),
                        "billing_unit": pricing.billing_unit,
                        "service_duration_type": pricing.service_duration_type,
                        "pricing_model": pricing.pricing_model,
                        "duration_value": pricing.duration_value,
                        "duration_minutes": pricing.duration_minutes,
                        "daily_capacity": pricing.daily_capacity,
                        "monthly_limit": pricing.monthly_limit,
                    }
            except Exception:
                pass
        except ProviderTemplateFacility.DoesNotExist:
            pass

    if not facility:
        # Fallback to service-only resolution
        provider_name = "Service Provider"
        if provider_id_param:
            try:
                from .models import ServiceProvider
                prov = ServiceProvider.objects.get(id=provider_id_param)
                provider_name = prov.verified_user.full_name or "Service Provider"
            except Exception: pass

        try:
            service_obj = ProviderTemplateService.objects.get(super_admin_service_id=service_id)
            return Response({
                "provider_name": provider_name,
                "service_name": service_obj.display_name,
                "category_name": "General",
                "facility_name": "Service",
                "price": "0.00"
            })
        except ProviderTemplateService.DoesNotExist:
            return Response({"error": "Service/Facility not found."}, status=status.HTTP_404_NOT_FOUND)

    # Resolve Provider Name from facility owner
    if facility:
        try:
            provider_name = facility.provider.full_name or "Service Provider"
        except Exception:
            if provider_id_param:
                try:
                    from .models import ServiceProvider
                    prov = ServiceProvider.objects.get(id=provider_id_param)
                    provider_name = prov.verified_user.full_name or "Service Provider"
                except Exception: pass

    # 🚀 Handle Consultation Type Override (VET)
    final_price = price_snapshot.get("price", str(getattr(facility, 'base_price', facility.price if not is_template else 0)))
    final_duration = price_snapshot.get("duration_minutes", facility.duration_minutes)

    if consultation_type_id:
        try:
            ct = ConsultationType.objects.get(id=consultation_type_id)
            final_price = str(ct.consultation_fee)
            final_duration = ct.duration_minutes
            price_snapshot["price"] = final_price
            price_snapshot["duration_minutes"] = final_duration
            price_snapshot["consultation_type_name"] = ct.name
        except ConsultationType.DoesNotExist:
            pass

    # 🚀 Handle Employee (Doctor) Specific Fee Override
    if employee_id:
        try:
            emp = OrganizationEmployee.objects.get(id=employee_id)
            if emp.consultation_fee > 0:
                final_price = str(emp.consultation_fee)
                price_snapshot["price"] = final_price
                price_snapshot["doctor_name"] = emp.full_name
                price_snapshot["specialization"] = emp.specialization
        except OrganizationEmployee.DoesNotExist:
            pass

    return Response({
        "provider_name": provider_name,
        "service_name": service_name,
        "category_name": category.name,
        "category_description": category.description or "",
        "facility_name": facility.name,
        "facility_description": facility.description or "",
        "protocol_type": getattr(facility, 'protocol_type', 'MINUTES_BASED'),
        "duration_minutes": final_duration,
        "pricing_strategy": getattr(facility, 'pricing_strategy', 'FIXED'),
        "base_price": str(getattr(facility, 'base_price', final_price)),
        "price_snapshot": price_snapshot,
        "is_medical": (service_name.upper() == "VETERINARY"),
        "price": final_price,
        "billing_unit": price_snapshot.get("billing_unit", "PER_SESSION"),
        "duration": final_duration
    })

from rest_framework import viewsets
from .models import DashboardWidget, UserDashboardLayout, VerifiedUser

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def widgets(self, request):
        """Returns all available dashboard widgets with their required capabilities."""
        widgets = DashboardWidget.objects.filter(is_active=True).order_by('order')
        data = []
        for w in widgets:
            data.append({
                "id": w.key,
                "name": w.label,
                "component": w.component_name,
                "required_capabilities": list(w.required_capabilities.values_list('key', flat=True)),
                "logic_type": w.logic_type,
                "order": w.order
            })
        return Response(data)

    @action(detail=False, methods=['get', 'post'], url_path='layout')
    def layout(self, request):
        """Gets or sets the user's custom dashboard layout."""
        # Standardize auth_user_id lookup
        auth_id = getattr(request.user, 'auth_user_id', None)
        if not auth_id:
            return Response({"error": "Auth ID missing"}, status=status.HTTP_400_BAD_REQUEST)
            
        vu = VerifiedUser.objects.filter(auth_user_id=auth_id).first()
        if not vu:
             return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)
             
        layout, _ = UserDashboardLayout.objects.get_or_create(user=vu)
        
        if request.method == 'POST':
            layout.layout_json = request.data.get('layout_json', [])
            layout.save()
            return Response({"status": "success", "layout": layout.layout_json})
            
        return Response({"layout_json": layout.layout_json})


# ============================================================
# CALENDAR FEED
# GET /api/provider/calendar-feed/?start=<ISO>&end=<ISO>
# Proxies BookingItems from customer_service formatted for FullCalendar.
# ============================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def calendar_feed(request):
    """
    Returns bookings for the authenticated provider in FullCalendar event format.
    Queries customer_service internally using the provider's JWT.
    """
    start = request.GET.get("start")
    end = request.GET.get("end")

    try:
        provider = ServiceProvider.objects.get(verified_user__auth_user_id=request.user.auth_user_id)
    except ServiceProvider.DoesNotExist:
        # Also handle employee case - get their org's provider
        try:
            emp = OrganizationEmployee.objects.get(auth_user_id=request.user.auth_user_id)
            provider = emp.organization
        except OrganizationEmployee.DoesNotExist:
            return Response({"error": "Provider profile not found"}, status=404)

    auth_header = request.headers.get("Authorization", "")
    params = {"provider_id": str(provider.id)}
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    events = []
    try:
        resp = requests.get(
            "http://127.0.0.1:8005/api/pet-owner/bookings/bookings/",
            headers={"Authorization": auth_header},
            params=params,
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("results", data) if isinstance(data, dict) else data
            # Flatten: bookings → items
            for booking in items:
                for item in booking.get("items", []):
                    snapshot = item.get("service_snapshot") or {}
                    duration = snapshot.get("duration_minutes", 60)
                    selected_time = item.get("selected_time")
                    end_time = item.get("end_time")
                    status_val = item.get("status", booking.get("status", "PENDING"))
                    color_map = {
                        "PENDING": "#F59E0B",
                        "CONFIRMED": "#3B82F6",
                        "IN_PROGRESS": "#8B5CF6",
                        "COMPLETED": "#10B981",
                        "CANCELLED": "#EF4444",
                        "REJECTED": "#94A3B8",
                    }
                    events.append({
                        "id": str(item.get("id", booking.get("id"))),
                        "title": f"{booking.get('pet_name', 'Pet')} – {snapshot.get('service_name', 'Service')}",
                        "start": selected_time,
                        "end": end_time,
                        "backgroundColor": color_map.get(status_val, "#94A3B8"),
                        "borderColor": "transparent",
                        "extendedProps": {
                            "status": status_val,
                            "pet_name": booking.get("pet_name"),
                            "service_name": snapshot.get("service_name"),
                            "employee_id": item.get("assigned_employee_id"),
                            "facility_id": item.get("facility_id"),
                            "duration_minutes": duration,
                            "booking_id": booking.get("id"),
                        },
                    })
    except Exception as e:
        logger.warning(f"[calendar_feed] Could not fetch from customer_service: {e}")
        # Return empty list rather than 500 – calendar renders empty gracefully
        return Response([])

    return Response(events)


# ============================================================
# RESOURCE OCCUPANCY
# GET /api/provider/resource-occupancy/
# Returns employee booking counts as resource utilisation for the Operations Hub.
# ============================================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resource_occupancy(request):
    """
    Returns a list of employee resource utilisation objects.
    Used by the OperationsCommandCenter to show workload per employee.
    """
    try:
        try:
            provider = ServiceProvider.objects.get(verified_user__auth_user_id=request.user.auth_user_id)
        except ServiceProvider.DoesNotExist:
            emp = OrganizationEmployee.objects.get(auth_user_id=request.user.auth_user_id)
            provider = emp.organization

        employees = OrganizationEmployee.objects.filter(
            organization=provider, deleted_at__isnull=True
        ).values("id", "full_name", "role", "specialization")

        # Fetch today's booking counts per employee from customer_service
        auth_header = request.headers.get("Authorization", "")
        today = timezone.now().date().isoformat()

        result = []
        for emp in employees:
            booking_count = 0
            try:
                resp = requests.get(
                    "http://127.0.0.1:8005/api/pet-owner/bookings/bookings/internal_employee_bookings/",
                    headers={"Authorization": auth_header},
                    params={"employee_id": str(emp["id"]), "date": today},
                    timeout=3,
                )
                if resp.status_code == 200:
                    booking_count = len(resp.json())
            except Exception:
                pass

            result.append({
                "employee_id": str(emp["id"]),
                "name": emp["full_name"] or "Employee",
                "role": emp["role"] or "Staff",
                "specialization": emp["specialization"] or "",
                "bookings_today": booking_count,
                "utilization_pct": min(booking_count * 10, 100),  # rough %: 10 bookings = 100%
            })

        return Response(result)

    except OrganizationEmployee.DoesNotExist:
        return Response({"error": "Provider profile not found"}, status=404)
    except Exception as e:
        logger.error(f"[resource_occupancy] Error: {e}")
        return Response([], status=200)
        return Response([], status=200)
