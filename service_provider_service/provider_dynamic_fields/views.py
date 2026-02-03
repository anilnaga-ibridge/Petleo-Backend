

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from provider_dynamic_fields.models import (
    LocalFieldDefinition,
    ProviderFieldValue,
)

from provider_dynamic_fields.serializers import (
    ProviderSubmitFieldSerializer,
    LocalFieldDefinitionSerializer,
    ProviderFieldValueSerializer,
)

from service_provider.models import VerifiedUser, OrganizationEmployee

import json


SUPERADMIN_URL = "http://127.0.0.1:8003/api/superadmin/definitions/public/"


def normalize_target(request):
    t = request.GET.get("target") or request.GET.get("role")
    if not t:
        return None
    t = t.strip().lower()
    return t if t in ["individual", "organization", "employee"] else None


# ----------------------------------------------------------
# 1) FETCH FIELD DEFINITIONS FROM SUPERADMIN
# ----------------------------------------------------------
class ProviderDynamicFieldsView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        target = normalize_target(request)

        if not target:
            return Response({"error": "Pass ?target="}, status=400)

        # Query local DB (synced via Kafka)
        local = LocalFieldDefinition.objects.filter(target=target)
        serializer = LocalFieldDefinitionSerializer(local, many=True)
        return Response({"fields": serializer.data}, status=200)


# ----------------------------------------------------------
# 2) SUBMIT FIELD VALUES + FILE UPLOAD (profile fields only)
# ----------------------------------------------------------
class ProviderFieldSubmitView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProviderSubmitFieldSerializer
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.GET.get("user")

        if not user:
            return Response({"error": "Missing ?user="}, status=400)

        # Validate verified user
        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "VerifiedUser not found"}, status=404)

        # ----------------------------
        # Parse JSON "fields"
        # ----------------------------
        raw_fields = request.data.get("fields", "[]")

        try:
            fields_data = json.loads(raw_fields)
        except:
            return Response({"error": "Invalid fields JSON"}, status=400)

        saved_fields = []

        # ----------------------------
        # SAVE NON-FILE FIELDS
        # ----------------------------
        for item in fields_data:
            field_id = item.get("field_id")
            value = item.get("value")
            metadata = item.get("metadata", {})

            if not field_id:
                continue

            # Validate field
            try:
                field_def = LocalFieldDefinition.objects.get(id=field_id)
            except:
                continue

            # Skip file fields → handled in file loop
            if field_def.field_type == "file":
                continue

            # Save text-based fields
            ProviderFieldValue.objects.update_or_create(
                verified_user=verified,
                field_id=field_id,
                defaults={"value": value, "metadata": metadata}
            )

            saved_fields.append({
                "field_id": field_id,
                "value": value
            })

        # ----------------------------
        # SAVE FILE FIELDS
        # ----------------------------
        saved_files = []
        field_ids = {str(item["field_id"]) for item in fields_data}

        for key, files in request.FILES.lists():
            if key not in field_ids:
                continue   # Not a profile field

            upload_file = files[0]

            obj, created = ProviderFieldValue.objects.update_or_create(
                verified_user=verified,
                field_id=key,
                defaults={
                    "file": upload_file,
                    "value": {"filename": upload_file.name},
                    "metadata": {
                        "size": upload_file.size,
                        "content_type": upload_file.content_type or ""
                    }
                }
            )

            saved_files.append({
                "field_id": key,
                "filename": upload_file.name,
                "size": upload_file.size,
                "content_type": getattr(upload_file, "content_type", ""),
                "file_url": request.build_absolute_uri(obj.file.url),
            })

        return Response({
            "saved_fields": saved_fields,
            "saved_files": saved_files
        }, status=201)


# ----------------------------------------------------------
# 3) GET ALL FIELD VALUES
# ----------------------------------------------------------
class ProviderFieldValuesListView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.GET.get("user")

        if not user:
            return Response({"error": "Missing ?user"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
        except:
            return Response({"error": "User not found"}, status=404)

        values = ProviderFieldValue.objects.filter(verified_user=verified)
        serializer = ProviderFieldValueSerializer(values, many=True)

        return Response({"values": serializer.data}, status=200)


# ----------------------------------------------------------
# 4) GET SINGLE FIELD
# ----------------------------------------------------------
class ProviderFieldValueDetailView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, field_id):
        user = request.GET.get("user")

        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
            obj = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
        except:
            return Response({"error": "Not found"}, status=404)

        ser = ProviderFieldValueSerializer(obj)
        return Response(ser.data)


# ----------------------------------------------------------
# 5) UPDATE SINGLE FIELD
# ----------------------------------------------------------
class ProviderFieldValueUpdateView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProviderSubmitFieldSerializer

    def put(self, request, field_id):
        user = request.GET.get("user")

        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
            obj = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
        except:
            return Response({"error": "Not found"}, status=404)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        obj.value = ser.validated_data.get("value")
        obj.metadata = ser.validated_data.get("metadata", {})
        obj.save()

        return Response({"message": "Updated"}, status=200)


# ----------------------------------------------------------
# 6) DELETE SINGLE FIELD
# ----------------------------------------------------------
class ProviderFieldValueDeleteView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def delete(self, request, field_id):
        user = request.GET.get("user")

        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
            obj = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
        except:
            return Response({"error": "Not found"}, status=404)

        obj.delete()
        return Response({"message": "Deleted"}, status=200)


# ==========================================================
# 7) PROVIDER CRUD VIEWSETS
# ==========================================================
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from service_provider.permissions import HasProviderPermission
from .models import ProviderCategory, ProviderFacility, ProviderPricing
from .serializers import ProviderCategorySerializer, ProviderFacilitySerializer, ProviderPricingSerializer

def get_effective_provider_user(auth_user):
    """
    Returns the VerifiedUser of the provider.
    If auth_user is an employee, returns the Organization's VerifiedUser.
    
    NOTE: auth_user is ALREADY a VerifiedUser instance due to VerifiedUserJWTAuthentication.
    """
    # print(f"DEBUG: get_effective_provider_user for {getattr(auth_user, 'email', 'Unknown')}")
    
    try:
        # 1. Check if employee
        # We must use auth_user.auth_user_id because OrganizationEmployee links via Auth ID
        employee = OrganizationEmployee.objects.get(auth_user_id=auth_user.auth_user_id)
        if employee.status == 'active':
            # print(f"DEBUG: User is active employee of {employee.organization.id}")
            return employee.organization.verified_user
    except OrganizationEmployee.DoesNotExist:
        pass
        
    # 2. Default to self (auth_user is already the VerifiedUser)
    return auth_user


class ProviderCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderCategorySerializer
    permission_classes = [IsAuthenticated, HasProviderPermission]

    def get_verified_user(self):
        return get_effective_provider_user(self.request.user)

    def get_queryset(self):
        qs = ProviderCategory.objects.filter(provider=self.get_verified_user()).order_by("-created_at")
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(provider=self.get_verified_user())

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk and str(pk).startswith("TEMPLATE_"):
            # Handle Template Deletion (Hide by removing permission)
            template_id = str(pk).replace("TEMPLATE_", "")
            from .models import ProviderCapabilityAccess, ProviderTemplateCategory
            
            try:
                t_cat = ProviderTemplateCategory.objects.get(id=template_id)
                sa_cat_id = t_cat.super_admin_category_id
                
                deleted_count, _ = ProviderCapabilityAccess.objects.filter(
                    user=self.get_verified_user(),
                    category_id=sa_cat_id
                ).delete()
                
                if deleted_count > 0:
                    return Response({"message": "Template category hidden"}, status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response({"error": "Permission not found"}, status=404)
                    
            except ProviderTemplateCategory.DoesNotExist:
                return Response({"error": "Template not found"}, status=404)
        
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk and str(pk).startswith("TEMPLATE_"):
            # Handle Template Edit (Shadowing)
            template_id = str(pk).replace("TEMPLATE_", "")
            from .models import ProviderCapabilityAccess, ProviderTemplateCategory
            
            try:
                t_cat = ProviderTemplateCategory.objects.get(id=template_id)
                sa_cat_id = t_cat.super_admin_category_id
                
                # 1. Create Real Category (Shadow)
                data = request.data.copy()
                data["service_id"] = t_cat.service.super_admin_service_id # Ensure service link
                
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                
                # 2. Hide Template
                ProviderCapabilityAccess.objects.filter(
                    user=self.get_verified_user(),
                    category_id=sa_cat_id
                ).delete()
                
                return Response(serializer.data, status=status.HTTP_200_OK)
                
            except ProviderTemplateCategory.DoesNotExist:
                return Response({"error": "Template not found"}, status=404)

        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        service_id = request.query_params.get("service")
        
        # 1. Custom Categories
        custom_qs = self.get_queryset()
        custom_data = self.get_serializer(custom_qs, many=True).data
        
        # 2. Template Categories
        template_data = []
        if service_id:
            from .models import ProviderTemplateCategory, ProviderTemplateService, ProviderTemplateFacility
            try:
                template_service = ProviderTemplateService.objects.get(super_admin_service_id=service_id)
                templates = ProviderTemplateCategory.objects.filter(service=template_service)
                
                # Filter out templates that already exist in custom_data (by name)
                existing_names = {c["name"] for c in custom_data}

                for t in templates:
                    if t.name in existing_names:
                        continue
                        
                    cat_dict = {
                        "id": f"TEMPLATE_{t.id}",
                        "original_id": t.super_admin_category_id,
                        "name": t.name,
                        "service_id": service_id,
                        "is_template": True,
                        "facilities": []
                    }
                    
                    # Fetch Template Facilities
                    facs = ProviderTemplateFacility.objects.filter(category=t)
                    for f in facs:
                        cat_dict["facilities"].append({
                            "id": f"TEMPLATE_{f.id}",
                            "name": f.name,
                            "description": f.description,
                            "price": "0.00",
                            "is_template": True
                        })
                    
                    template_data.append(cat_dict)
                        
            except ProviderTemplateService.DoesNotExist:
                pass

        # 3. Merge
        combined = template_data + custom_data
        
        # 4. Inject Permissions
        from provider_dynamic_fields.models import ProviderCapabilityAccess
        
        perms = ProviderCapabilityAccess.objects.filter(user=request.user)
        if service_id:
            perms = perms.filter(service_id=service_id)
        # Map: category_id -> list of permissions
        perm_map = {}
        facility_perm_map = {}
        service_level_perms = []
        
        for p in perms:
            if p.facility_id:
                fid = str(p.facility_id)
                facility_perm_map[fid] = p
            elif p.category_id:
                cid = str(p.category_id)
                if cid not in perm_map:
                    perm_map[cid] = []
                perm_map[cid].append(p)
            elif p.service_id and not p.category_id and not p.facility_id:
                # Service-level permission (applies to all categories)
                service_level_perms.append(p)

        final_data = []
        for item in combined:
            is_template = item.get("is_template", False)
            item["is_template"] = is_template
            
            # Determine if user is the owner
            is_owner = (request.user.auth_user_id == self.get_verified_user().auth_user_id)
            
            if is_owner:
                item["can_view"] = True
                item["can_create"] = True
                item["can_edit"] = True
                item["can_delete"] = True
                for f in item.get("facilities", []):
                    f["can_view"] = True
                    f["can_create"] = True
                    f["can_edit"] = True
                    f["can_delete"] = True
            else:
                # For employees, we MUST check permissions even for custom data
                s_id = str(item.get("service_id"))
                # For custom data, original_id might not be set, use id
                c_id = str(item.get("original_id") or item.get("id"))
                
                category_perms = perm_map.get(c_id, []) + service_level_perms
                
                can_view = False
                can_create = False
                can_edit = False
                can_delete = False
                
                for p in category_perms:
                    if p.can_view: can_view = True
                    if not p.facility_id:
                        if p.can_create: can_create = True
                        if p.can_edit: can_edit = True
                        if p.can_delete: can_delete = True
                
                item["can_view"] = can_view
                item["can_create"] = can_create
                item["can_edit"] = can_edit
                item["can_delete"] = can_delete

                # Inject Facility Permissions
                for f in item.get("facilities", []):
                    f_id = str(f.get("original_id") or f.get("id"))
                    f_perm = facility_perm_map.get(f_id)
                    
                    if f_perm:
                        f["can_view"] = f_perm.can_view
                        f["can_create"] = f_perm.can_create
                        f["can_edit"] = f_perm.can_edit
                        f["can_delete"] = f_perm.can_delete
                    else:
                        # Fallback to category permissions
                        f["can_view"] = can_view
                        f["can_create"] = can_create
                        f["can_edit"] = can_edit
                        f["can_delete"] = can_delete

            final_data.append(item)

        return Response(final_data)


class ProviderFacilityViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderFacilitySerializer
    permission_classes = [IsAuthenticated, HasProviderPermission]

    def get_verified_user(self):
        return get_effective_provider_user(self.request.user)

    def get_queryset(self):
        qs = ProviderFacility.objects.filter(provider=self.get_verified_user()).order_by("-created_at")
        service_id = self.request.query_params.get("service")
        if service_id:
            # Filter facilities by categories belonging to the service
            qs = qs.filter(category__service_id=service_id)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        category_id = data.get("category")

        if category_id and str(category_id).startswith("TEMPLATE_"):
            # Resolve Template Category
            from .models import ProviderTemplateCategory, ProviderCategory
            
            # Extract original ID
            # Format: TEMPLATE_<uuid> or just TEMPLATE_<id>
            # But wait, in list() we set id = f"TEMPLATE_{t.id}" where t.id is the LOCAL PK of ProviderTemplateCategory
            # So we need to strip "TEMPLATE_" and find the ProviderTemplateCategory
            
            try:
                template_pk = str(category_id).replace("TEMPLATE_", "")
                template_cat = ProviderTemplateCategory.objects.get(id=template_pk)
                
                # Check if a real ProviderCategory already exists for this template
                # We need a way to link them. 
                # Currently ProviderCategory has `service_id` and `name`.
                # It does NOT have a link to `ProviderTemplateCategory`.
                # But we can match by name and service_id?
                # Or we should have added `original_template_id` to ProviderCategory?
                
                # For now, let's match by name and service_id
                real_cat = ProviderCategory.objects.filter(
                    provider=self.get_verified_user(),
                    service_id=template_cat.service.super_admin_service_id,
                    name=template_cat.name
                ).first()
                
                if not real_cat:
                    # Create it
                    real_cat = ProviderCategory.objects.create(
                        provider=self.get_verified_user(),
                        service_id=template_cat.service.super_admin_service_id,
                        name=template_cat.name,
                        is_active=True
                    )
                
                data["category"] = real_cat.id
                
            except (ProviderTemplateCategory.DoesNotExist, ValueError):
                return Response({"error": "Invalid template category ID"}, status=400)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(provider=self.get_verified_user())

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk and str(pk).startswith("TEMPLATE_"):
            # Handle Template Deletion (Hide by removing permission)
            template_id = str(pk).replace("TEMPLATE_", "")
            from .models import ProviderCapabilityAccess, ProviderTemplateFacility
            
            try:
                t_fac = ProviderTemplateFacility.objects.get(id=template_id)
                sa_fac_id = t_fac.super_admin_facility_id
                
                deleted_count, _ = ProviderCapabilityAccess.objects.filter(
                    user=self.get_verified_user(),
                    facility_id=sa_fac_id
                ).delete()
                
                if deleted_count > 0:
                    return Response({"message": "Template facility hidden"}, status=status.HTTP_204_NO_CONTENT)
                else:
                    return Response({"error": "Permission not found"}, status=404)
                    
            except ProviderTemplateFacility.DoesNotExist:
                return Response({"error": "Template not found"}, status=404)
        
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk and str(pk).startswith("TEMPLATE_"):
            # Handle Template Edit (Shadowing)
            template_id = str(pk).replace("TEMPLATE_", "")
            from .models import ProviderCapabilityAccess, ProviderTemplateFacility
            
            try:
                t_fac = ProviderTemplateFacility.objects.get(id=template_id)
                sa_fac_id = t_fac.super_admin_facility_id
                
                # 1. Create Real Facility (Shadow)
                data = request.data.copy()
                # We need to ensure category is set correctly.
                # If the user is editing a facility, they might be changing its category too.
                # But usually they just change name/price.
                # If they don't send category, we should use the template's category (resolved to real).
                
                if not data.get("category"):
                    # Resolve template category to real category
                    from .models import ProviderCategory, ProviderTemplateCategory
                    t_cat = t_fac.category
                    real_cat = ProviderCategory.objects.filter(
                        provider=self.get_verified_user(),
                        service_id=t_cat.service.super_admin_service_id,
                        name=t_cat.name
                    ).first()
                    
                    if not real_cat:
                        real_cat = ProviderCategory.objects.create(
                            provider=self.get_verified_user(),
                            service_id=t_cat.service.super_admin_service_id,
                            name=t_cat.name,
                            is_active=True
                        )
                    data["category"] = real_cat.id

                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                
                # 2. Hide Template
                ProviderCapabilityAccess.objects.filter(
                    user=self.get_verified_user(),
                    facility_id=sa_fac_id
                ).delete()
                
                return Response(serializer.data, status=status.HTTP_200_OK)
                
            except ProviderTemplateFacility.DoesNotExist:
                return Response({"error": "Template not found"}, status=404)

        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        service_id = request.query_params.get("service")
        
        # 1. Custom Facilities
        custom_qs = self.get_queryset()
        custom_data = self.get_serializer(custom_qs, many=True).data
        
        # 2. Template Facilities
        template_data = []
        if service_id:
            from .models import ProviderTemplateFacility, ProviderTemplateCategory, ProviderTemplateService
            try:
                # We need facilities belonging to categories of this service
                template_service = ProviderTemplateService.objects.get(super_admin_service_id=service_id)
                categories = ProviderTemplateCategory.objects.filter(service=template_service)
                templates = ProviderTemplateFacility.objects.filter(category__in=categories)
                
                for t in templates:
                    cat_id_debug = f"TEMPLATE_{t.category.id}"
                    template_data.append({
                        "id": f"TEMPLATE_{t.id}",
                        "original_id": t.super_admin_facility_id,
                        "category_id": f"TEMPLATE_{t.category.id}",
                        "name": t.name,
                        "description": t.description,
                        "is_template": True
                    })
            except ProviderTemplateService.DoesNotExist:
                pass
        
        category_param = request.query_params.get("category")
        if category_param:
            print(f"DEBUG: Facility List requested for category {category_param}")
            # Filter custom data
            custom_data = [d for d in custom_data if str(d.get("category")) == str(category_param)]
            
            # Fetch Templates for this category
            if str(category_param).startswith("TEMPLATE_"):
                # ... existing logic ...
                from .models import ProviderTemplateFacility, ProviderTemplateCategory
                try:
                    cat_pk = str(category_param).replace("TEMPLATE_", "")
                    t_cat = ProviderTemplateCategory.objects.get(id=cat_pk)
                    t_facs = ProviderTemplateFacility.objects.filter(category=t_cat)
                    
                    template_data = [] 
                    for t in t_facs:
                        template_data.append({
                            "id": f"TEMPLATE_{t.id}",
                            "original_id": t.super_admin_facility_id,
                            "category_id": f"TEMPLATE_{t.category.id}",
                            "name": t.name,
                            "description": t.description,
                            "is_template": True
                        })
                except ProviderTemplateCategory.DoesNotExist:
                    pass
            else:
                 # Real Category ID passed. 
                 print(f"DEBUG: Real Category ID passed: {category_param}")
                 from .models import ProviderCategory, ProviderTemplateCategory, ProviderTemplateFacility
                 try:
                     real_cat = ProviderCategory.objects.get(id=category_param)
                     print(f"DEBUG: Found Real Category: {real_cat.name} (Service: {real_cat.service_id})")
                     
                     # Match template by name/service
                     t_cat = ProviderTemplateCategory.objects.filter(
                         service__super_admin_service_id=real_cat.service_id,
                         name=real_cat.name
                     ).first()
                     
                     if t_cat:
                         print(f"DEBUG: Found matching Template Category: {t_cat.name} (ID: {t_cat.id})")
                         t_facs = ProviderTemplateFacility.objects.filter(category=t_cat)
                         print(f"DEBUG: Found {t_facs.count()} template facilities")
                         
                         template_data = []
                         for t in t_facs:
                            fac_entry = {
                                "id": f"TEMPLATE_{t.id}",
                                "original_id": t.super_admin_facility_id,
                                "category_id": str(real_cat.id), # Use the real category ID as parent
                                "name": t.name,
                                "description": t.description,
                                "is_template": True
                            }
                            template_data.append(fac_entry)
                            print(f"DEBUG: Added facility: {t.name}")
                     else:
                         print("DEBUG: No matching Template Category found")
                         
                 except (ProviderCategory.DoesNotExist, Exception) as e:
                     print(f"DEBUG: Error finding category or template: {e}")
                     pass

        # 3. Merge
        combined = template_data + custom_data
        print(f"DEBUG: Returning {len(combined)} facilities")

        # 4. Inject Permissions
        from provider_dynamic_fields.models import ProviderCapabilityAccess
        perms = ProviderCapabilityAccess.objects.filter(user=request.user)
        
        # Map: facility_id -> perm
        perm_map = {}
        category_level_perms = {}
        service_level_perms = []

        for p in perms:
            if p.facility_id:
                perm_map[str(p.facility_id)] = p
            elif p.category_id:
                category_level_perms[str(p.category_id)] = p
            elif p.service_id:
                service_level_perms.append(p)

        final_data = []
        for item in combined:
            is_template = item.get("is_template", False)
            item["is_template"] = is_template
            
            # Determine if user is the owner
            is_owner = (request.user.auth_user_id == self.get_verified_user().auth_user_id)
            
            if is_owner:
                item["can_view"] = True
                item["can_create"] = True
                item["can_edit"] = True
                item["can_delete"] = True
            else:
                f_id = str(item.get("original_id") or item.get("id"))
                c_id = str(item.get("category_id"))
                
                perm = perm_map.get(f_id)
                
                if not perm:
                    # Fallback to Category level
                    perm = category_level_perms.get(c_id)
                
                if not perm and service_level_perms:
                    # Fallback to Service level
                    perm = service_level_perms[0]
                
                if perm:
                    item["can_view"] = perm.can_view
                    item["can_create"] = perm.can_create
                    item["can_edit"] = perm.can_edit
                    item["can_delete"] = perm.can_delete
                else:
                    item["can_view"] = False
                    item["can_create"] = False
                    item["can_edit"] = False
                    item["can_delete"] = False
            
            final_data.append(item)
        return Response(final_data)


class ProviderPricingViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderPricingSerializer
    permission_classes = [IsAuthenticated, HasProviderPermission]

    def get_verified_user(self):
        return get_effective_provider_user(self.request.user)

    def get_queryset(self):
        qs = ProviderPricing.objects.filter(provider=self.get_verified_user()).order_by("-created_at")
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs


    def perform_create(self, serializer):
        serializer.save(provider=self.get_verified_user())

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        facility_id = data.get("facility")
        category_id = data.get("category_id")

        # Helper to resolve/create Category
        def resolve_category(template_cat_id):
            from .models import ProviderTemplateCategory, ProviderCategory
            try:
                t_cat = ProviderTemplateCategory.objects.get(id=template_cat_id)
                real_cat = ProviderCategory.objects.filter(
                    provider=self.get_verified_user(),
                    service_id=t_cat.service.super_admin_service_id,
                    name=t_cat.name
                ).first()
                
                if not real_cat:
                    real_cat = ProviderCategory.objects.create(
                        provider=self.get_verified_user(),
                        service_id=t_cat.service.super_admin_service_id,
                        name=t_cat.name,
                        is_active=True
                    )
                return real_cat
            except ProviderTemplateCategory.DoesNotExist:
                return None

        # 1. Handle Facility Template
        if facility_id and str(facility_id).startswith("TEMPLATE_"):
            from .models import ProviderTemplateFacility, ProviderFacility
            try:
                t_fac_id = str(facility_id).replace("TEMPLATE_", "")
                t_fac = ProviderTemplateFacility.objects.get(id=t_fac_id)
                
                # Ensure Category exists first
                real_cat = resolve_category(t_fac.category.id)
                if not real_cat:
                    return Response({"error": "Could not resolve template category for facility"}, status=400)
                
                # Find or Create Real Facility
                real_fac = ProviderFacility.objects.filter(
                    provider=self.get_verified_user(),
                    category=real_cat,
                    name=t_fac.name
                ).first()
                
                if not real_fac:
                    real_fac = ProviderFacility.objects.create(
                        provider=self.get_verified_user(),
                        category=real_cat,
                        name=t_fac.name,
                        description=t_fac.description,
                        is_active=True
                    )
                
                data["facility"] = real_fac.id
                data["category_id"] = str(real_cat.id) # Ensure consistency
                
            except ProviderTemplateFacility.DoesNotExist:
                return Response({"error": "Invalid template facility ID"}, status=400)

        # 2. Handle Category Template (if no facility or facility didn't resolve it)
        elif category_id and str(category_id).startswith("TEMPLATE_"):
            t_cat_id = str(category_id).replace("TEMPLATE_", "")
            real_cat = resolve_category(t_cat_id)
            if real_cat:
                data["category_id"] = str(real_cat.id)
            else:
                return Response({"error": "Invalid template category ID"}, status=400)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk and str(pk).startswith("TEMPLATE_"):
            # Handle Template Deletion (Shadowing with is_active=False)
            template_id = str(pk).replace("TEMPLATE_", "")
            from .models import ProviderTemplatePricing, ProviderPricing, ProviderCategory, ProviderFacility
            
            try:
                t_price = ProviderTemplatePricing.objects.get(id=template_id)
                
                # Resolve/Create Local Category & Facility
                # Use facility's category if pricing's category is None
                t_fac = t_price.facility
                if t_fac:
                    t_cat = t_fac.category
                else:
                    t_cat = t_price.category
                
                if not t_cat:
                     return Response({"error": "Template category not found"}, status=400)

                real_cat = ProviderCategory.objects.filter(
                    provider=self.get_verified_user(),
                    service_id=t_cat.service.super_admin_service_id,
                    name=t_cat.name
                ).first()
                
                if not real_cat:
                    real_cat = ProviderCategory.objects.create(
                        provider=self.get_verified_user(),
                        service_id=t_cat.service.super_admin_service_id,
                        name=t_cat.name,
                        is_active=True
                    )
                
                real_fac = None
                if t_fac:
                    real_fac = ProviderFacility.objects.filter(
                        provider=self.get_verified_user(),
                        category=real_cat,
                        name=t_fac.name
                    ).first()
                    
                    if not real_fac:
                        real_fac = ProviderFacility.objects.create(
                            provider=self.get_verified_user(),
                            category=real_cat,
                            name=t_fac.name,
                            description=t_fac.description,
                            is_active=True
                        )
                
                # Create Inactive Shadow Pricing
                ProviderPricing.objects.create(
                    provider=self.get_verified_user(),
                    service_id=t_price.service.super_admin_service_id,
                    category_id=str(real_cat.id),
                    facility=real_fac,
                    price=t_price.price,
                    duration=t_price.duration,
                    description=t_price.description,
                    is_active=False # This hides it
                )
                
                return Response({"message": "Template pricing hidden"}, status=status.HTTP_204_NO_CONTENT)
                    
            except ProviderTemplatePricing.DoesNotExist:
                return Response({"error": "Template not found"}, status=404)
        
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk and str(pk).startswith("TEMPLATE_"):
            # Handle Template Edit (Shadowing)
            template_id = str(pk).replace("TEMPLATE_", "")
            from .models import ProviderTemplatePricing, ProviderPricing, ProviderCategory, ProviderFacility
            
            try:
                t_price = ProviderTemplatePricing.objects.get(id=template_id)
                
                # Resolve/Create Local Category & Facility
                t_fac = t_price.facility
                if t_fac:
                    t_cat = t_fac.category
                else:
                    t_cat = t_price.category

                if not t_cat:
                     return Response({"error": "Template category not found"}, status=400)

                real_cat = ProviderCategory.objects.filter(
                    provider=self.get_verified_user(),
                    service_id=t_cat.service.super_admin_service_id,
                    name=t_cat.name
                ).first()
                
                if not real_cat:
                    real_cat = ProviderCategory.objects.create(
                        provider=self.get_verified_user(),
                        service_id=t_cat.service.super_admin_service_id,
                        name=t_cat.name,
                        is_active=True
                    )
                
                real_fac = None
                if t_fac:
                    real_fac = ProviderFacility.objects.filter(
                        provider=self.get_verified_user(),
                        category=real_cat,
                        name=t_fac.name
                    ).first()
                    
                    if not real_fac:
                        real_fac = ProviderFacility.objects.create(
                            provider=self.get_verified_user(),
                            category=real_cat,
                            name=t_fac.name,
                            description=t_fac.description,
                            is_active=True
                        )

                # Create Active Shadow Pricing with New Data
                data = request.data.copy()
                data["service_id"] = t_price.service.super_admin_service_id
                data["category_id"] = str(real_cat.id)
                data["facility"] = real_fac.id if real_fac else None
                
                if not data.get("duration"):
                    data["duration"] = t_price.duration

                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                
                return Response(serializer.data, status=status.HTTP_200_OK)
                
            except ProviderTemplatePricing.DoesNotExist:
                return Response({"error": "Template not found"}, status=404)

        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        service_id = request.query_params.get("service")
        
        # 1. Custom Pricing
        custom_qs = self.get_queryset()
        custom_data = self.get_serializer(custom_qs, many=True).data
        
        # 2. Template Pricing
        template_data = []
        if service_id:
            from .models import ProviderTemplatePricing, ProviderTemplateService
            try:
                template_service = ProviderTemplateService.objects.get(super_admin_service_id=service_id)
                templates = ProviderTemplatePricing.objects.filter(service=template_service)
                
                # Pre-fetch existing real categories to avoid N+1
                real_cats_map = {} # template_cat_id_str -> real_cat_obj
                try:
                    from .models import ProviderCategory, ProviderTemplateCategory
                    # Find categories for this service belonging to this provider
                    real_cats = ProviderCategory.objects.filter(
                        provider=self.get_verified_user(), 
                        service_id=service_id
                    )
                    for rc in real_cats:
                        # Find corresponding template cat
                        # This is tricky because real_cat doesn't store template_id directly
                        # We have to match by name
                        real_cats_map[rc.name] = rc
                except Exception:
                    pass

                for t in templates:
                    # Derive category from pricing first, then facility
                    t_cat_name = None
                    t_cat_id_raw = None
                    
                    if t.category:
                        t_cat_name = t.category.name
                        t_cat_id_raw = t.category.id
                    elif t.facility and t.facility.category:
                        t_cat_name = t.facility.category.name
                        t_cat_id_raw = t.facility.category.id

                    # Default to template ID
                    cat_id = f"TEMPLATE_{t_cat_id_raw}" if t_cat_id_raw else None
                    cat_name = t_cat_name or "All Categories"
                    
                    # Try to match with Real Category
                    if t_cat_name and t_cat_name in real_cats_map:
                        rc = real_cats_map[t_cat_name]
                        cat_id = str(rc.id)
                        # cat_name = rc.name # Should be same

                    template_data.append({
                        "id": f"TEMPLATE_{t.id}",
                        "original_id": str(t.id),
                        "service_id": service_id,
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "facility": t.facility.super_admin_facility_id if t.facility else None,
                        "facility_name": t.facility.name if t.facility else "All Facilities",
                        "price": str(t.price),
                        "duration": t.duration,
                        "description": t.description,
                        "is_template": True,
                        "is_active": True
                    })
            except ProviderTemplateService.DoesNotExist:
                pass

        # 3. Shadowing Logic
        # Map Custom Pricing (Local IDs) to Template Pricing (SA IDs) via Name Matching
        sa_fac_map = {} # (category_name, facility_name) -> sa_facility_id
        if service_id:
            from .models import ProviderTemplateFacility, ProviderTemplateCategory, ProviderTemplateService
            try:
                ts = ProviderTemplateService.objects.get(super_admin_service_id=service_id)
                t_cats = ProviderTemplateCategory.objects.filter(service=ts)
                t_facs = ProviderTemplateFacility.objects.filter(category__in=t_cats)
                for tf in t_facs:
                    sa_fac_map[(tf.category.name, tf.name)] = tf.super_admin_facility_id
            except:
                pass

        # Fetch ALL custom pricing (active and inactive)
        all_custom = ProviderPricing.objects.filter(provider=self.get_verified_user())
        if service_id:
            all_custom = all_custom.filter(service_id=service_id)
            
        shadow_map = set()
        for p in all_custom:
            f_sa_id = None
            if p.facility:
                cat_name = p.facility.category.name if p.facility.category else None
                fac_name = p.facility.name
                if cat_name and fac_name:
                    f_sa_id = sa_fac_map.get((cat_name, fac_name))
            
            f_key = f_sa_id if f_sa_id else (str(p.facility.id) if p.facility else "None")
            s = str(p.service_id) if p.service_id else "None"
            d = str(p.duration)
            shadow_map.add((s, f_key, d))

        # 4. Merge
        final_list = []
        
        # Add Templates (if not shadowed)
        for t in template_data:
            s = str(t["service_id"])
            f = str(t["facility"]) if t["facility"] else "None"
            d = str(t["duration"])
            
            if (s, f, d) not in shadow_map:
                final_list.append(t)
                
        # Add Custom (even inactive ones, as they might be disabled by user)
        for c in custom_data:
            # We add ALL custom data, because inactive ones represent "disabled" facilities
            final_list.append(c)

        # 5. Inject Permissions
        from provider_dynamic_fields.models import ProviderCapabilityAccess
        perms = ProviderCapabilityAccess.objects.filter(user=request.user)
        if service_id:
            perms = perms.filter(service_id=service_id)
            
        perm_map = {}
        for p in perms:
            s = str(p.service_id) if p.service_id else "None"
            c = str(p.category_id) if p.category_id else "None"
            f = str(p.facility_id) if p.facility_id else "None"
            perm_map[(s, c, f)] = p

        final_data = []
        for item in final_list:
            is_template = item.get("is_template", False)
            item["is_template"] = is_template
            
            # Determine if user is the owner
            is_owner = (request.user.auth_user_id == self.get_verified_user().auth_user_id)
            
            if is_owner:
                item["can_view"] = True
                item["can_create"] = True
                item["can_edit"] = True
                item["can_delete"] = True
            else:
                s = str(item.get("service_id")) if item.get("service_id") else "None"
                c = str(item.get("category_id")) if item.get("category_id") else "None"
                f = str(item.get("facility")) if item.get("facility") else "None"
                
                perm = perm_map.get((s, c, f))
                if not perm:
                    perm = perm_map.get((s, c, "None"))
                if not perm:
                    perm = perm_map.get((s, "None", "None"))
                
                if perm:
                    item["can_view"] = perm.can_view
                    item["can_create"] = perm.can_create
                    item["can_edit"] = perm.can_edit
                    item["can_delete"] = perm.can_delete
                else:
                    item["can_view"] = False
                    item["can_create"] = False
                    item["can_edit"] = False
                    item["can_delete"] = False

            final_data.append(item)

        return Response(final_data)
