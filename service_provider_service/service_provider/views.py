from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


from .models import (
    ServiceProvider, 
    VerifiedUser,
    AllowedService,
    Capability,
    ProviderRole,
    OrganizationEmployee,
    PermissionAuditLog,
)
from .serializers import (
    ServiceProviderSerializer, 
    CapabilitySerializer,
    ProviderRoleSerializer,
)

class ServiceProviderProfileView(APIView):
    """
    POST: Create or update the service provider profile, including personal info, avatar, and status.
    """

    def post(self, request):
        # Extract the auth_user_id from the request body
        auth_user_id = request.data.get('auth_user_id')
        
        # Check if auth_user_id is provided
        if not auth_user_id:
            return Response({"error": "auth_user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to fetch the VerifiedUser by auth_user_id
        try:
            verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "VerifiedUser not found for this auth_user_id"}, status=status.HTTP_404_NOT_FOUND)

        # Now, try to fetch the ServiceProvider related to this VerifiedUser
        provider, created = ServiceProvider.objects.get_or_create(verified_user=verified_user)

        # Proceed to update the profile data
        serializer = ServiceProviderSerializer(provider, data=request.data, partial=True)
        
        if serializer.is_valid():
            avatar_file = request.FILES.get('avatar')

            if avatar_file:
                provider.avatar = avatar_file
                provider.avatar_size = f"{round(avatar_file.size / 1024, 2)} KB"
                provider.save(update_fields=["avatar", "avatar_size"])

            serializer.save()

            return Response({
                "message": "Provider profile updated successfully",
                "data": ServiceProviderSerializer(provider).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ServiceProviderDetailView(APIView):
    """
    GET: Fetch service provider profile by auth_user_id.
    """
    permission_classes = [AllowAny]

    def get(self, request, auth_user_id):
        try:
            verified_user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
            provider = ServiceProvider.objects.get(verified_user=verified_user)
            return Response(ServiceProviderSerializer(provider).data)
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
    try:
        emp_record = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        if emp_record.provider_role:
             display_role = emp_record.provider_role.name
    except OrganizationEmployee.DoesNotExist:
        pass

    # Get avatar
    avatar_url = None
    try:
        from service_provider.models import ServiceProvider
        # Corrected lookup: verified_user__auth_user_id
        provider = ServiceProvider.objects.filter(verified_user__auth_user_id=user.auth_user_id).first()
        if provider and provider.avatar:
            avatar_url = request.build_absolute_uri(provider.avatar.url)
            print(f"✅ [Port 8002] AVATAR READY for {user.email}: {avatar_url}")
        else:
            print(f"⚠️ [Port 8002] NO AVATAR found for {user.email}")
    except Exception as e:
        print(f"❌ [Port 8002] AVATAR ERROR for {user.email}: {str(e)}")

    user_profile = {
        "fullName": user.full_name,
        "email": user.email,
        "phoneNumber": user.phone_number,
        "role": display_role,
        "avatar": avatar_url
    }
    
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
    print("\\n" + "="*100)
    print("🚨 NEW CODE LOADED - VINOD FIX ACTIVE 🚨")
    print("="*100 + "\\n")
    
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
    # IMPORTANT: For employees, we build the tree from the organization owner's capabilities,
    # then filter by the employee's role permissions below
    permissions_list = _build_permission_tree(subscription_owner)
    
    with open("debug_perms.log", "a") as f:
        f.write(f"\\n[{timezone.now()}] get_my_permissions | User: {user.email} ({user.auth_user_id})\\n")
        f.write(f"Subscription Owner: {subscription_owner.email}\\n")
        f.write(f"Tree Count: {len(permissions_list)}\\n")
        for p in permissions_list:
            f.write(f" - {p.get('service_key')} ({p.get('service_name')})\\n")

    # --- INJECT DYNAMIC CAPABILITIES (Grooming, Daycare, etc.) ---
    # These might be simple capability keys not yet linked to full Service Templates
    
    # 1. Get all capability keys for the user
    user_caps = set()
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        
        print(f"\n{'='*100}")
        print(f"🧑‍💼 EMPLOYEE PERMISSION CALCULATION: {user.email}")
        print(f"{'='*100}")
        print(f"   Employee ID: {emp.id}")
        print(f"   Role Field: {emp.role}")
        print(f"   Provider Role: {emp.provider_role}")
        print(f"   Status: {emp.status}")
        
        # CASE A: Employee
        # Access = Organization Plan ∩ Employee Role
        user_caps = set(emp.get_final_permissions())
        
        print(f"   📊 Final Permissions Count: {len(user_caps)}")
        print(f"   📋 Final Permissions: {list(user_caps)}")
        print(f"{'='*100}\n")
        
        # IMPORTANT: Filter the permission tree by employee capabilities
        # The tree was built from org plan, but we need to restrict it to role capabilities
        print(f"🔍 Filtering permission tree by employee capabilities...")
        print(f"   Tree size before filter: {len(permissions_list)}")
        
        filtered_permissions = []
        for service in permissions_list:
            service_key = service.get('service_key')
            service_name = service.get('service_name')
            
            print(f"   🔍 Checking service: {service_name} (key: {service_key})")
            print(f"      Service key in user_caps? {service_key in user_caps}")
            
            # Check if employee has access to this service
            if service_key in user_caps:
                print(f"      ✅ MATCH - Service accessible, now filtering categories...")
                
                # CRITICAL FIX: Even if service is accessible, filter categories by employee caps
                filtered_categories = []
                for category in service.get('categories', []):
                    cat_key = category.get('linked_capability') or category.get('category_key')
                    cat_name = category.get('name') or category.get('category_name')
                    print(f"         Category: {cat_name} (key: {cat_key})")
                    
                    # Check if employee has this specific category capability
                    if cat_key and cat_key in user_caps:
                        print(f"            ✅ Category MATCH - Including")
                        filtered_categories.append(category)
                    else:
                        print(f"            ❌ Category NO MATCH - Excluding")
                
                # Include service with filtered categories
                filtered_service = service.copy()
                filtered_service['categories'] = filtered_categories
                filtered_permissions.append(filtered_service)
                print(f"      ➕ Added service with {len(filtered_categories)} filtered categories")
                
            else:
                print(f"      ❌ NO MATCH - Checking if any categories match...")
                # Check categories - maybe they have access to specific categories
                filtered_categories = []
                for category in service.get('categories', []):
                    cat_key = category.get('linked_capability') or category.get('category_key')
                    cat_name = category.get('name') or category.get('category_name')
                    print(f"         Category: {cat_name} (key: {cat_key})")
                    if cat_key and cat_key in user_caps:
                        print(f"            ✅ Category MATCH")
                        filtered_categories.append(category)
                    else:
                        print(f"            ❌ Category NO MATCH")
                
                # If employee has access to any categories, include service with filtered categories
                if filtered_categories:
                    print(f"      ➕ Adding service with {len(filtered_categories)} filtered categories")
                    filtered_service = service.copy()
                    filtered_service['categories'] = filtered_categories
                    filtered_permissions.append(filtered_service)
                else:
                    print(f"      ⏭️ SKIPPING - No matching categories")
        
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
            # For dynamic services, this comes from Service.linked_capability
            cap_key = allowed_svc.name.upper().replace(" ", "_").replace("&", "")
            
            print(f"       Checking: {allowed_svc.name} → {cap_key}")
            
            # Check if user has this capability
            if cap_key in user_caps:
                print(f"          ✅ MATCH! Adding to tree")
                # Skip VETERINARY_CORE if we already have a real Veterinary service from a plan
                if cap_key == "VETERINARY_CORE" and any("VETERINARY" in (p.get("service_key") or "").upper() for p in permissions_list):
                    print(f"          ⏭️ Skipping (already have VETERINARY service)")
                    continue

                # Check if already present to avoid duplicates
                if not any(p.get('service_key') == cap_key for p in permissions_list):
                    permissions_list.append({
                        "service_id": str(allowed_svc.service_id),
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
                    print(f"          ⏭️ Already in list")
            else:
                print(f"          ❌ NO MATCH (not in user_caps)")
    
        print(f"   Final Tree Count: {len(permissions_list)}\n")
    else:
        print(f"\n⏭️ SKIPPING ALLOWED SERVICE INJECTION (Employee - already filtered)\n")
    # -----------------------------------------
    
    # Construct response
    plan_data = None
    if valid_sub:
        plan_data = {
            "title": valid_sub.plan_title,
            "subtitle": f"{valid_sub.billing_cycle_name} Plan",
            "start_date": valid_sub.start_date,
            "end_date": valid_sub.end_date,
            "days_left": getattr(valid_sub, 'days_left', None),
            "is_expiring_soon": getattr(valid_sub, 'is_expiring_soon', False)
        }

    response_data = {
        "permissions": permissions_list,
        "plan": plan_data,
        "user_profile": user_profile
    }

    print(f"✅ DEBUG RESPONSE get_my_permissions: Found {len(permissions_list)} Services")
    for p in permissions_list:
        print(f"   SERVICE: {p.get('service_name')} (Key: {p.get('service_key')}, ID: {p.get('service_id')}) [View: {p.get('can_view')}]")

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
from .models import OrganizationEmployee, ServiceProvider
from .serializers import OrganizationEmployeeSerializer
from .permissions import IsOrganizationAdmin

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    Manage employees for the logged-in organization.
    """
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    serializer_class = OrganizationEmployeeSerializer
    
    def get_queryset(self):
        # Return employees where organization owner is the logged-in user
        user = self.request.user
        
        with open("debug_views.log", "a") as f:
            f.write(f"\\n[{timezone.now()}] Request User: {user} (ID: {user.id}) Role: {getattr(user, 'role', 'N/A')}\\n")
        
        # Find the ServiceProvider associated with the logged-in user
        try:
            provider = ServiceProvider.objects.get(verified_user=user)
            with open("debug_views.log", "a") as f:
                f.write(f"[{timezone.now()}] Found Provider: {provider.id}\\n")
            
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
                f.write(f"[{timezone.now()}] Error in get_queryset: {e}\\n")
            return OrganizationEmployee.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Proxy staff creation to Auth Service.
        """
        # 1. Prepare data for Auth Service
        auth_data = {
            "full_name": request.data.get("full_name"),
            "email": request.data.get("email"),
            "phone_number": request.data.get("phone_number"),
            "role": request.data.get("role"),
        }
        
        # 2. Call Auth Service to register
        auth_header = request.headers.get('Authorization')
        try:
            # Auth Service is at 8000
            auth_url = "http://localhost:8000/auth/api/auth/register/"
            response = requests.post(
                auth_url,
                json=auth_data,
                headers={"Authorization": auth_header}
            )
            
            if response.status_code != 201:
                return Response(response.json(), status=response.status_code)
            
            # The Kafka consumer will handle creating the OrganizationEmployee record.
            # But we can return the auth response which contains user details.
            return Response(response.json(), status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": f"Failed to connect to Auth Service: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


class EmployeeAssignmentViewSet(viewsets.ViewSet):
    """
    Manage service assignments for employees.
    Supports granular permissions (Service -> Category -> Facility).
    """
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

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
            employee = OrganizationEmployee.objects.get(id=pk, organization=provider)
        except (ServiceProvider.DoesNotExist, OrganizationEmployee.DoesNotExist):
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
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get_queryset(self):
        try:
            provider = ServiceProvider.objects.get(verified_user=self.request.user)
            return ProviderRole.objects.filter(provider=provider)
        except ServiceProvider.DoesNotExist:
            return ProviderRole.objects.none()

    def perform_create(self, serializer):
        provider = ServiceProvider.objects.get(verified_user=self.request.user)
        role = serializer.save(provider=provider)
        
        # 🛡️ Audit Log
        PermissionAuditLog.log_action(
            actor=self.request.user,
            action='ROLE_CREATED',
            target_role=role,
            details={
                'name': role.name,
                'description': role.description
            },
            request=self.request
        )

    def perform_update(self, serializer):
        role = serializer.save()
        
        # 🛡️ Audit Log
        PermissionAuditLog.log_action(
            actor=self.request.user,
            action='ROLE_UPDATED',
            target_role=role,
            details={
                'name': role.name,
                'description': role.description
            },
            request=self.request
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        role_name = instance.name
        role_id = instance.id
        logger.info(f"🗑️ Attempting to delete ProviderRole: {role_name} ({role_id})")
        
        # 🛡️ Audit Log
        PermissionAuditLog.log_action(
            actor=self.request.user,
            action='ROLE_DELETED',
            details={
                'name': role_name,
                'id': str(role_id)
            },
            request=self.request
        )
        
        instance.delete()

        # 1. Explicit Model-based Cleanup of Capabilities
        # Avoids reverse-manager ambiguity
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_access(request):
    """
    Returns allowed modules for the dynamic sidebar.
    GET /api/provider/permissions/my-access/
    """
    user = request.user
    
    # 1. Get Effective Capability Keys
    capability_keys = set()
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        capability_keys = set(emp.get_final_permissions())
    except OrganizationEmployee.DoesNotExist:
        # Organization/Individual Owner
        # Fetch from ProviderCapability table (New Dynamic System)
        capability_keys = set(user.dynamic_capabilities.filter(is_active=True).values_list('capability__key', flat=True))
        
    # 2. Fetch Modules for these keys
    from .models import FeatureModule
    modules = FeatureModule.objects.filter(capability__key__in=capability_keys, is_active=True).values(
        'name', 'route', 'icon', 'sequence', 'key'
    ).order_by('sequence')
    
    return Response({
        "capabilities": list(capability_keys),
        "modules": list(modules)
    })

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
        from .models import ProviderRole, ProviderRoleCapability, OrganizationEmployee
        
        # 0. Special Handling for Organization Admin/Owner
        if role_name.lower() in ['admin', 'owner', 'organization', 'individual']:
            from .models import VerifiedUser
            user = VerifiedUser.objects.filter(auth_user_id=org_id).first()
            if user:
                caps = list(user.get_all_plan_capabilities())
                return Response({"role": role_name, "capabilities": caps, "source": "organization_plan"})
        
        # 1. Check for Custom Provider Role
        role = ProviderRole.objects.filter(provider__verified_user__auth_user_id=org_id, name__iexact=role_name).first()
        if role:
            caps = list(ProviderRoleCapability.objects.filter(provider_role=role).values_list('capability_key', flat=True))
            # Always ensure VETERINARY_CORE if it has any VETERINARY_* caps
            if any(c.startswith('VETERINARY_') for c in caps) and 'VETERINARY_CORE' not in caps:
                caps.append('VETERINARY_CORE')
            return Response({"role": role_name, "capabilities": caps, "source": "custom_role"})
            
        # 2. Fallback to Legacy Map (System Defaults)
        caps = OrganizationEmployee.LEGACY_ROLE_MAP.get(role_name.lower(), [])
        if caps:
             return Response({"role": role_name, "capabilities": caps, "source": "legacy_map"})

        return Response({"role": role_name, "capabilities": ["VETERINARY_CORE"], "source": "fallback"})
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)
