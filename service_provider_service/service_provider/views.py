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

    user_profile = {
        "fullName": user.full_name,
        "email": user.email,
        "role": display_role
    }

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
    permissions_list = _build_permission_tree(user)
    
    with open("debug_perms.log", "a") as f:
        f.write(f"\\n[{timezone.now()}] get_my_permissions | User: {user.email} ({user.auth_user_id})\\n")
        f.write(f"Tree Count: {len(permissions_list)}\\n")
        for p in permissions_list:
            f.write(f" - {p.get('service_key')} ({p.get('service_name')})\\n")

    # --- INJECT DYNAMIC CAPABILITIES (Grooming, Daycare, etc.) ---
    # These might be simple capability keys not yet linked to full Service Templates
    
    # 1. Get all capability keys for the user
    user_caps = set()
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        # CASE A: Employee
        # Access = Organization Plan ∩ Employee Role
        user_caps = set(emp.get_final_permissions())
        print(f"DEBUG: Employee {user.email} permissions: {len(user_caps)}")
        
    except OrganizationEmployee.DoesNotExist:
        # CASE B: Provider (Org or Individual)
        # Access = Purchased Plan (Upper Bound)
        # We do NOT intersect with "role defaults" anymore.
        
        user_caps = user.get_all_plan_capabilities()
        
        # Ensure CORE access is always present
        user_caps.add("VETERINARY_CORE")
        
        print(f"DEBUG: Provider {user.email} Plan Caps: {len(user_caps)}")

    simple_services = {
        "GROOMING": {"name": "Grooming", "icon": "tabler-cut"},
        "DAYCARE": {"name": "Daycare", "icon": "tabler-bone"},
        "TRAINING": {"name": "Training", "icon": "tabler-school"},
        "BOARDING": {"name": "Boarding", "icon": "tabler-home"},
        "VETERINARY_VISITS": {"name": "Visits", "icon": "tabler-calendar"},
        "VETERINARY_VITALS": {"name": "Vitals", "icon": "tabler-activity"},
        "VETERINARY_PRESCRIPTIONS": {"name": "Prescriptions", "icon": "tabler-pill"},
        "VETERINARY_LABS": {"name": "Lab Orders", "icon": "tabler-microscope"},
        "VETERINARY_MEDICINE_REMINDERS": {"name": "Medicine", "icon": "tabler-alarm"},
        "VETERINARY_DOCTOR": {"name": "Doctor Queue", "icon": "tabler-stethoscope"},
        "VETERINARY_PHARMACY": {"name": "Pharmacy", "icon": "tabler-band-aid"},
        "VETERINARY_CORE": {"name": "Veterinary", "icon": "tabler-stethoscope"}
    }

    for key, meta in simple_services.items():
        # Check if user has this capability key
        if key in user_caps:
            # Skip VETERINARY_CORE if we already have a real Veterinary service from a plan
            if key == "VETERINARY_CORE" and any("VETERINARY" in (p.get("service_key") or "").upper() for p in permissions_list):
                continue

            # Check if already present to avoid duplicates
            if not any(p.get('service_key') == key for p in permissions_list):
                permissions_list.append({
                    "service_id": key, # Use Key as ID for simple services
                    "service_name": meta["name"],
                    "service_key": key,
                    "icon": meta["icon"],
                    "categories": [],
                    "can_view": True,
                    "can_create": True,
                    "can_edit": True,
                    "can_delete": True
                })
    # -----------------------------------------
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
        
        # Sync with Auth Service (optional, but good practice)
        from .kafka_producer import publish_employee_updated
        publish_employee_updated(employee)
        
        return Response({'status': 'DISABLED'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        employee = self.get_object()
        employee.status = 'ACTIVE'
        employee.save()
        
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
        employee = serializer.save()
        
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
        serializer.save(provider=provider)

    @transaction.atomic
    def perform_destroy(self, instance):
        role_name = instance.name
        role_id = instance.id
        logger.info(f"🗑️ Attempting to delete ProviderRole: {role_name} ({role_id})")

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
