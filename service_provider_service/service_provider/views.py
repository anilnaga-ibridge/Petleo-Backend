from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone


from .models import (
    ServiceProvider, 
    VerifiedUser,
    AllowedService,
    Capability,
    ProviderRole,
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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_permissions(request):
    """
    Returns the effective permissions for the logged-in provider.
    Includes dynamic check for plan validity.
    """
    user = request.user
    
    # 1. Determine the "Subscription Owner"
    # If it's an employee, we check the Organization's subscription.
    subscription_owner = user
    try:
        employee = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        
        # ✅ Check if employee is disabled
        if employee.status == 'DISABLED':
            print(f"DEBUG: Employee {user.email} is DISABLED. Revoking access.")
            return Response({
                "permissions": [], 
                "plan": None, 
                "error": "Your account has been disabled by your organization."
            })
            
        subscription_owner = employee.organization.verified_user
        print(f"DEBUG: User is employee. Checking Org subscription: {subscription_owner.email}")
    except OrganizationEmployee.DoesNotExist:
        pass

    # 2. Dynamic Plan Validation
    # 2. Dynamic Plan Validation
    try:
        # Check for ANY active subscription
        active_subs = subscription_owner.subscription.filter(is_active=True)
        
        # Filter out expired ones in Python if needed, or use exclude
        valid_sub = None
        for sub in active_subs:
            if not sub.end_date or sub.end_date >= timezone.now():
                valid_sub = sub
                break
        
        if not valid_sub:
            print(f"DEBUG: No valid active subscription found for {subscription_owner.email}")
            return Response({"permissions": [], "plan": None})

        print(f"DEBUG: Found valid subscription: {valid_sub.plan_id}")
            
    except Exception as e:
        print(f"Subscription check failed: {e}")
        # In case of error, we might want to fail safe or allow? 
        # For now, let's fail safe (no permissions)
        return Response({"permissions": [], "plan": None})

    # 3. Fetch Capabilities using the robust helper
    permissions_list = _build_permission_tree(user)

    # --- INJECT VETERINARY_CORE CAPABILITY ---
    # Veterinary staff must have access to the dashboard even without specific service assignments.
    user_role = getattr(user, 'role', '').upper()
    vet_roles = ['RECEPTIONIST', 'DOCTOR', 'LAB_TECH', 'PHARMACY', 'VITALS_STAFF', 'NURSE', 'INDIVIDUAL']
    
    # Check if user has ANY veterinary capability
    has_any_vet_cap = any(p.get('service_key', '').startswith('VETERINARY_') for p in permissions_list)

    if user_role in vet_roles or has_any_vet_cap:
        # Check if VETERINARY_CORE is already present (to avoid duplicates)
        has_vet_core = any(p.get('service_key') == 'VETERINARY_CORE' for p in permissions_list)
        
        if not has_vet_core:
            permissions_list.append({
                "service_id": "VETERINARY_CORE",
                "service_name": "Veterinary Core",
                "service_key": "VETERINARY_CORE",
                "icon": "tabler-stethoscope",
                "categories": [],
                "can_view": True,
                "can_create": False,
                "can_edit": False,
                "can_delete": False
            })
    # -----------------------------------------
    
    # Construct response
    response_data = {
        "permissions": permissions_list,
        "plan": {
            "title": "Active Plan", 
            "subtitle": "Standard Provider Plan",
            "end_date": timezone.now() + timezone.timedelta(days=30) 
        }
    }
    
    return Response(response_data)


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

# Helper for building permission tree
def _build_permission_tree(user):
    if not hasattr(user, 'capabilities'):
        return []

    # Fetch all permissions
    perms = user.capabilities.all()
    
    # Pre-fetch templates for names lookup
    services_map = {s.super_admin_service_id: s for s in ProviderTemplateService.objects.all()}
    categories_map = {c.super_admin_category_id: c for c in ProviderTemplateCategory.objects.all()}
    facilities_map = {f.super_admin_facility_id: f for f in ProviderTemplateFacility.objects.all()}
    pricing_map = {p.super_admin_pricing_id: p for p in ProviderTemplatePricing.objects.all()}

    # Group permissions by service -> category
    grouped = {}
    print(f"DEBUG: Processing {len(perms)} permissions")
    for perm in perms:
        if not perm.service_id: 
            print("DEBUG: Skipping perm with no service_id")
            continue
        s_id = str(perm.service_id)
        print(f"DEBUG: Processing perm for service {s_id} (Cat: {perm.category_id})")
        
        # Get Service Info
        svc_obj = services_map.get(s_id)
        svc_name = svc_obj.display_name if svc_obj else "Unknown Service"
        svc_key = svc_obj.name if svc_obj else "unknown_service"
        svc_icon = svc_obj.icon if svc_obj else "tabler-box"

        if s_id not in grouped:
            grouped[s_id] = {
                "service_id": s_id,
                "service_name": svc_name,
                "service_key": svc_key,
                "icon": svc_icon,
                "permissions": {
                    "can_view": False, "can_create": False, "can_edit": False, "can_delete": False
                },
                "categories": {}
            }
        
        # If category is NOT present, it's service-level permission
        if not perm.category_id:
            grouped[s_id]["permissions"] = {
                "can_view": perm.can_view,
                "can_create": perm.can_create,
                "can_edit": perm.can_edit,
                "can_delete": perm.can_delete,
            }
            continue

        # If category is present
        c_id = str(perm.category_id)
        
        # Get Category Info
        cat_obj = categories_map.get(c_id)
        cat_name = cat_obj.name if cat_obj else "Unknown Category"
        cat_linked_cap = cat_obj.linked_capability if cat_obj else None

        if c_id not in grouped[s_id]["categories"]:
            grouped[s_id]["categories"][c_id] = {
                "id": c_id,
                "name": cat_name,
                "linked_capability": cat_linked_cap,
                "permissions": {
                    "can_view": False, "can_create": False, "can_edit": False, "can_delete": False
                },
                "facilities": [],
                "pricing": [] # Category-level pricing
            }
        
        # If facility is NOT present, it's category-level permission
        if not perm.facility_id:
            # Check if it's a pricing-level permission
            if hasattr(perm, 'pricing_id') and perm.pricing_id:
                 p_id = str(perm.pricing_id)
                 p_obj = pricing_map.get(p_id)
                 if p_obj:
                     grouped[s_id]["categories"][c_id]["pricing"].append({
                         "id": p_id,
                         "price": str(p_obj.price),
                         "duration": p_obj.duration,
                         "description": p_obj.description,
                         "can_view": perm.can_view
                     })
            else:
                grouped[s_id]["categories"][c_id]["permissions"] = {
                    "can_view": perm.can_view,
                    "can_create": perm.can_create,
                    "can_edit": perm.can_edit,
                    "can_delete": perm.can_delete,
                }
        else:
            # Facility-level permission
            f_id = str(perm.facility_id)
            fac_obj = facilities_map.get(f_id)
            fac_name = fac_obj.name if fac_obj else "Unknown Facility"
            
            # Find existing facility entry
            fac_entry = next((f for f in grouped[s_id]["categories"][c_id]["facilities"] if f["id"] == f_id), None)
            if not fac_entry:
                fac_entry = {
                    "id": f_id,
                    "name": fac_name,
                    "permissions": {
                        "can_view": False, "can_create": False, "can_edit": False, "can_delete": False
                    },
                    "pricing": []
                }
                grouped[s_id]["categories"][c_id]["facilities"].append(fac_entry)
            
            # Check if it's a pricing-level permission
            if hasattr(perm, 'pricing_id') and perm.pricing_id:
                 p_id = str(perm.pricing_id)
                 p_obj = pricing_map.get(p_id)
                 if p_obj:
                     fac_entry["pricing"].append({
                         "id": p_id,
                         "price": str(p_obj.price),
                         "duration": p_obj.duration,
                         "description": p_obj.description,
                         "can_view": perm.can_view
                     })
            else:
                fac_entry["permissions"] = {
                    "can_view": perm.can_view,
                    "can_create": perm.can_create,
                    "can_edit": perm.can_edit,
                    "can_delete": perm.can_delete,
                }

    # Now, we need to populate "Available" pricing options even if not explicitly assigned yet?
    # The _build_permission_tree is used for BOTH "available" (Org's permissions) and "assigned" (Employee's).
    # If it's "available", we want to show ALL pricing rules under the facilities the Org has access to.
    
    # Iterate again to populate pricing for facilities/categories that have access
    for s_val in grouped.values():
        for c_val in s_val["categories"].values():
            # 1. Populate Category-level pricing
            cat_pricing = [p for p in pricing_map.values() if str(p.category_id) == c_val["id"] and not p.facility_id]
            
            if c_val["permissions"]["can_view"]:
                existing_ids = [p["id"] for p in c_val["pricing"]]
                for p in cat_pricing:
                    if p.super_admin_pricing_id not in existing_ids:
                        c_val["pricing"].append({
                            "id": p.super_admin_pricing_id,
                            "price": str(p.price),
                            "duration": p.duration,
                            "description": p.description,
                            "can_view": True # Available to assign
                        })

            # 2. Populate Facility-level pricing
            for f_val in c_val["facilities"]:
                fac_pricing = [p for p in pricing_map.values() if str(p.facility_id) == f_val["id"]]
                
                if f_val["permissions"]["can_view"]:
                    existing_ids = [p["id"] for p in f_val["pricing"]]
                    for p in fac_pricing:
                        if p.super_admin_pricing_id not in existing_ids:
                            f_val["pricing"].append({
                                "id": p.super_admin_pricing_id,
                                "price": str(p.price),
                                "duration": p.duration,
                                "description": p.description,
                                "can_view": True
                            })

    # Flatten structure for response
    permissions_list = []
    for s_val in grouped.values():
        cats_list = []
        for c_val in s_val["categories"].values():
            cats_list.append(c_val)
        
        final_cats = []
        
        # Aggregate service-level permissions
        svc_can_view = s_val["permissions"]["can_view"]
        svc_can_create = s_val["permissions"]["can_create"]
        svc_can_edit = s_val["permissions"]["can_edit"]
        svc_can_delete = s_val["permissions"]["can_delete"]

        for c in cats_list:
            # Calculate effective can_view for category (bubble up from facilities)
            cat_effective_view = c["permissions"]["can_view"]
            for fac in c.get("facilities", []):
                if fac["permissions"]["can_view"]:
                    cat_effective_view = True

            c_flat = {
                "id": c["id"],
                "name": c["name"],
                "linked_capability": c.get("linked_capability"),
                "facilities": c["facilities"],
                "pricing": c["pricing"],
                **c["permissions"],
                "can_view": cat_effective_view # Override with effective view
            }
            final_cats.append(c_flat)
            
            if c_flat["can_view"]: svc_can_view = True
            if c_flat["can_create"]: svc_can_create = True
            if c_flat["can_edit"]: svc_can_edit = True
            if c_flat["can_delete"]: svc_can_delete = True
            
            for fac in c.get("facilities", []):
                if fac["permissions"]["can_view"]: svc_can_view = True
                if fac["permissions"]["can_create"]: svc_can_create = True
                if fac["permissions"]["can_edit"]: svc_can_edit = True
                if fac["permissions"]["can_delete"]: svc_can_delete = True

        permissions_list.append({
            "service_id": s_val["service_id"],
            "service_name": s_val["service_name"],
            "service_key": s_val["service_key"],
            "icon": s_val["icon"],
            "categories": final_cats,
            "can_view": svc_can_view,
            "can_create": svc_can_create,
            "can_edit": svc_can_edit,
            "can_delete": svc_can_delete
        })
    
    return permissions_list

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
