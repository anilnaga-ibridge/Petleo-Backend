from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone


from .models import (
    ServiceProvider, 
    VerifiedUser,
)
from .serializers import (
    ServiceProviderSerializer, 
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
    ProviderTemplateFacility
)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_my_permissions(request):
    """
    GET /api/provider/permissions/
    Returns rich permissions structure for the logged-in provider.
    """
    try:
        verified_user = request.user
        
        # Structure expected by frontend:
        # {
        #   permissions: [
        #     { service_id, service_name, can_view, can_create, ..., categories: [...] }
        #   ],
        #   plan: { title, subtitle, end_date }
        # }

        if not hasattr(verified_user, 'capabilities'):
            return Response({"permissions": [], "plan": None})

        # Fetch all permissions
        perms = verified_user.capabilities.all()
        
        # Pre-fetch templates for names lookup
        services_map = {s.super_admin_service_id: s for s in ProviderTemplateService.objects.all()}
        categories_map = {c.super_admin_category_id: c for c in ProviderTemplateCategory.objects.all()}
        facilities_map = {f.super_admin_facility_id: f for f in ProviderTemplateFacility.objects.all()}

        # Group permissions by service -> category
        grouped = {}
        
        for perm in perms:
            if not perm.service_id:
                continue
                
            s_id = str(perm.service_id)
            
            # Get Service Info
            svc_obj = services_map.get(s_id)
            svc_name = svc_obj.display_name if svc_obj else "Unknown Service"
            svc_icon = svc_obj.icon if svc_obj else "tabler-box"

            if s_id not in grouped:
                grouped[s_id] = {
                    "service_id": s_id,
                    "service_name": svc_name,
                    "icon": svc_icon,
                    "categories": {}
                }
            
            # If category is present
            if perm.category_id:
                c_id = str(perm.category_id)
                
                # Get Category Info
                cat_obj = categories_map.get(c_id)
                cat_name = cat_obj.name if cat_obj else "Unknown Category"

                if c_id not in grouped[s_id]["categories"]:
                    grouped[s_id]["categories"][c_id] = {
                        "id": c_id,
                        "name": cat_name,
                        "permissions": {
                            "can_view": False, "can_create": False, "can_edit": False, "can_delete": False
                        },
                        "facilities": []
                    }
                
                # If facility is NOT present, it's category-level permission
                if not perm.facility_id:
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
                    
                    grouped[s_id]["categories"][c_id]["facilities"].append({
                        "id": f_id,
                        "name": fac_name,
                        "permissions": {
                            "can_view": perm.can_view,
                            "can_create": perm.can_create,
                            "can_edit": perm.can_edit,
                            "can_delete": perm.can_delete,
                        }
                    })

        # Flatten structure for response
        permissions_list = []
        for s_val in grouped.values():
            cats_list = []
            for c_val in s_val["categories"].values():
                cats_list.append(c_val)
            
            # We need to merge category-level permissions into the category object
            # The frontend expects: { id, name, facilities: [], ...permissions }
            # My structure above has "permissions" nested. Let's flatten it.
            
            final_cats = []
            
            # Aggregate service-level permissions
            svc_can_view = False
            svc_can_create = False
            svc_can_edit = False
            svc_can_delete = False

            for c in cats_list:
                c_flat = {
                    "id": c["id"],
                    "name": c["name"],
                    "facilities": c["facilities"],
                    **c["permissions"]
                }
                final_cats.append(c_flat)
                
                # OR logic: if allowed in any category, allowed in service
                if c["permissions"]["can_view"]: svc_can_view = True
                if c["permissions"]["can_create"]: svc_can_create = True
                if c["permissions"]["can_edit"]: svc_can_edit = True
                if c["permissions"]["can_delete"]: svc_can_delete = True
                
                # Also check facility-level permissions
                for fac in c.get("facilities", []):
                    if fac["permissions"]["can_view"]: svc_can_view = True
                    if fac["permissions"]["can_create"]: svc_can_create = True
                    if fac["permissions"]["can_edit"]: svc_can_edit = True
                    if fac["permissions"]["can_delete"]: svc_can_delete = True

            permissions_list.append({
                "service_id": s_val["service_id"],
                "service_name": s_val["service_name"],
                "icon": s_val["icon"],
                "categories": final_cats,
                "can_view": svc_can_view,
                "can_create": svc_can_create,
                "can_edit": svc_can_edit,
                "can_delete": svc_can_delete
            })

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
    except Exception as e:
        import traceback
        print(traceback.format_exc())
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
        
        if not hasattr(verified_user, 'capabilities'):
            print("DEBUG: User has no capabilities relation")
            return Response([])

        # Get unique service IDs from capabilities
        service_ids = verified_user.capabilities.values_list('service_id', flat=True).distinct()
        print(f"DEBUG: Found service_ids in capabilities: {list(service_ids)}")
        
        # Fetch details from templates
        services = ProviderTemplateService.objects.filter(super_admin_service_id__in=service_ids)
        print(f"DEBUG: Found {services.count()} matching ProviderTemplateService objects")
        
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
