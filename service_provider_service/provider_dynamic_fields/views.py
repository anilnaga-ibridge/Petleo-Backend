

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

from service_provider.models import VerifiedUser

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

class ProviderCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderCategorySerializer
    permission_classes = [IsAuthenticated, HasProviderPermission]

    def get_verified_user(self):
        return VerifiedUser.objects.get(auth_user_id=self.request.user.id)

    def get_queryset(self):
        qs = ProviderCategory.objects.filter(provider=self.get_verified_user()).order_by("-created_at")
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(provider=self.get_verified_user())

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
                
                for t in templates:
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
        
        perms = ProviderCapabilityAccess.objects.filter(user=self.get_verified_user())
        if service_id:
            perms = perms.filter(service_id=service_id)
        # Map: category_id -> list of permissions
        perm_map = {}
        for p in perms:
            if p.category_id:
                cid = str(p.category_id)
                if cid not in perm_map:
                    perm_map[cid] = []
                perm_map[cid].append(p)

        final_data = []
        for item in combined:
            is_template = item.get("is_template", False)
            item["is_template"] = is_template
            
            if not is_template:
                item["can_view"] = True
                item["can_create"] = True
                item["can_edit"] = True
                item["can_delete"] = True
            else:
                s_id = str(item.get("service_id"))
                c_id = str(item.get("original_id"))
                
                category_perms = perm_map.get(c_id, [])
                
                # Aggregate permissions
                # If ANY permission (category or facility level) grants view, then category is viewable
                can_view = False
                can_create = False
                can_edit = False
                can_delete = False
                
                for p in category_perms:
                    if p.can_view: can_view = True
                    # For create/edit/delete, we might want to be stricter, 
                    # but for now let's assume if you have power over a facility, you might need to see the category.
                    # Actually, category-level actions (like renaming the category) should probably be restricted.
                    # But the user wants to SEE the categories.
                    
                    # If it's a direct category permission (facility_id=None), it definitely applies
                    if not p.facility_id:
                        if p.can_create: can_create = True
                        if p.can_edit: can_edit = True
                        if p.can_delete: can_delete = True
                
                item["can_view"] = can_view
                item["can_create"] = can_create
                item["can_edit"] = can_edit
                item["can_delete"] = can_delete

            final_data.append(item)

        return Response(final_data)


class ProviderFacilityViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderFacilitySerializer
    permission_classes = [IsAuthenticated, HasProviderPermission]

    def get_verified_user(self):
        return VerifiedUser.objects.get(auth_user_id=self.request.user.id)

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
                    template_data.append({
                        "id": f"TEMPLATE_{t.id}",
                        "original_id": t.super_admin_facility_id,
                        "category_id": t.category.super_admin_category_id,
                        "name": t.name,
                        "description": t.description,
                        "is_template": True
                    })
            except ProviderTemplateService.DoesNotExist:
                pass

        # 3. Merge
        combined = template_data + custom_data

        # 4. Inject Permissions
        # 4. Inject Permissions
        from provider_dynamic_fields.models import ProviderCapabilityAccess
        perms = ProviderCapabilityAccess.objects.filter(user=self.get_verified_user())
        
        # Map: facility_id -> perm
        perm_map = {}
        for p in perms:
            if p.facility_id:
                perm_map[str(p.facility_id)] = p

        final_data = []
        for item in combined:
            is_template = item.get("is_template", False)
            item["is_template"] = is_template
            
            if not is_template:
                item["can_view"] = True
                item["can_create"] = True
                item["can_edit"] = True
                item["can_delete"] = True
            else:
                f_id = str(item.get("original_id"))
                
                perm = perm_map.get(f_id)
                
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
        return VerifiedUser.objects.get(auth_user_id=self.request.user.id)
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
                
                for t in templates:
                    template_data.append({
                        "id": f"TEMPLATE_{t.id}",
                        "original_id": str(t.id),
                        "service_id": service_id,
                        "category_id": t.category.super_admin_category_id if t.category else None,
                        "category_name": t.category.name if t.category else "All Categories",
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

        # 3. Merge
        combined = template_data + custom_data

        # 4. Inject Permissions
        # 4. Inject Permissions
        from provider_dynamic_fields.models import ProviderCapabilityAccess
        perms = ProviderCapabilityAccess.objects.filter(user=self.get_verified_user())
        if service_id:
            perms = perms.filter(service_id=service_id)
            
        perm_map = {}
        for p in perms:
            k = (str(p.service_id), str(p.category_id) if p.category_id else None)
            perm_map[k] = p

        final_data = []
        for item in combined:
            is_template = item.get("is_template", False)
            item["is_template"] = is_template
            
            if not is_template:
                item["can_view"] = True
                item["can_create"] = True
                item["can_edit"] = True
                item["can_delete"] = True
            else:
                s_id = str(item.get("service_id"))
                c_id = str(item.get("category_id")) if item.get("category_id") else None
                
                perm = perm_map.get((s_id, c_id))
                if not perm:
                    perm = perm_map.get((s_id, None))
                
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
    def get_queryset(self):
        # Filter by service if provided in query params
        qs = ProviderPricing.objects.filter(provider=self.get_verified_user()).order_by("-created_at")
        service_id = self.request.query_params.get("service")
        if service_id:
            qs = qs.filter(service_id=service_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(provider=self.get_verified_user())
