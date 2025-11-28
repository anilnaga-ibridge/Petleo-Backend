# # views.py (NO KAFKA VERSION)
# # views.py

# from rest_framework import generics, status
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny

# from dynamic_fields.models import LocalFieldDefinition, ProviderFieldValue
# from dynamic_fields.serializers import (
#     ProviderSubmitFieldSerializer,
#     LocalFieldDefinitionSerializer
# )

# from service_provider.models import VerifiedUser
# import requests


# import requests

# SUPERADMIN_URL = "http://127.0.0.1:8003/api/superadmin/definitions/public/"


# # Utility to normalize target
# def normalize_target(request):
#     target = request.GET.get("target") or request.GET.get("role")
#     if not target:
#         return None

#     target = target.strip().lower()
#     if target not in ["individual", "organization", "employee"]:
#         return None

#     return target


# # ============================================================
# # 1) GET Dynamic Fields — Always Fetch From SuperAdmin
# # ============================================================
# class ProviderDynamicFieldsView(generics.GenericAPIView):
#     permission_classes = [AllowAny]

#     def get(self, request):
#         target = normalize_target(request)

#         if not target:
#             return Response(
#                 {"error": "Pass ?target=individual / organization / employee"},
#                 status=400,
#             )

#         # 1️⃣ Fetch from SuperAdmin
#         try:
#             url = f"{SUPERADMIN_URL}?target={target}"
#             res = requests.get(url, timeout=5)

#             if res.status_code == 200:
#                 fields = res.json()

#                 # 🔥 Save/update in LocalFieldDefinition
#                 for f in fields:
#                     LocalFieldDefinition.objects.update_or_create(
#                         id=f["id"],
#                         defaults={
#                             "target": f["target"],
#                             "name": f["name"],
#                             "label": f["label"],
#                             "field_type": f["field_type"],
#                             "is_required": f["is_required"],
#                             "options": f.get("options", []),
#                             "order": f.get("order", 0),
#                             "help_text": f.get("help_text", ""),
#                         },
#                     )

#                 return Response({"fields": fields}, status=200)

#         except Exception as e:
#             print("SuperAdmin unreachable:", e)

#         # 2️⃣ Fallback Local DB
#         local_fields = LocalFieldDefinition.objects.filter(target=target)
#         serialized = LocalFieldDefinitionSerializer(local_fields, many=True).data

#         return Response({"fields": serialized}, status=200)


# # ============================================================
# # 2) SUBMIT Provider Dynamic Values — Validate With SuperAdmin
# # ============================================================
# # =============================================================================
# # 2) PUBLIC — SUBMIT Dynamic Values (NO KAFKA, NO PROVIDER_TYPE)
# # =============================================================================
# class ProviderFieldSubmitView(generics.GenericAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = ProviderSubmitFieldSerializer

#     def post(self, request):
#         # read user
#         auth_user_id = request.GET.get("user")
#         if not auth_user_id:
#             return Response({"error": "Pass ?user=<auth_user_id>"}, status=400)

#         # get verified user
#         try:
#             verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
#         except VerifiedUser.DoesNotExist:
#             return Response({"error": "Verified user not found"}, status=400)

#         # validate request body
#         serializer = self.get_serializer(data=request.data, many=True)
#         serializer.is_valid(raise_exception=True)

#         saved_items, errors = [], []

#         # process each field
#         for item in serializer.validated_data:
#             field_id = item["field_id"]
#             value = item.get("value")
#             metadata = item.get("metadata", {})

#             # ensure field exists locally
#             if not LocalFieldDefinition.objects.filter(id=field_id).exists():
#                 errors.append({"field_id": field_id, "error": "Unknown field"})
#                 continue

#             obj, created = ProviderFieldValue.objects.update_or_create(
#                 verified_user=verified,
#                 field_id=field_id,
#                 defaults={"value": value, "metadata": metadata},
#             )

#             saved_items.append({
#                 "field_id": field_id,
#                 "value": value,
#                 "saved": True,
#                 "created": created,
#             })

#         return Response(
#             {"saved": saved_items, "errors": errors},
#             status=200,
#         )



from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from dynamic_fields.models import LocalFieldDefinition, ProviderFieldValue
from dynamic_fields.serializers import (
    ProviderSubmitFieldSerializer,
    LocalFieldDefinitionSerializer
)
from service_provider.models import VerifiedUser
import requests

SUPERADMIN_URL = "http://127.0.0.1:8003/api/superadmin/definitions/public/"


# ----------------------------------------------------------
# Utility
# ----------------------------------------------------------
def normalize_target(request):
    target = request.GET.get("target") or request.GET.get("role")
    if not target:
        return None

    target = target.strip().lower()
    if target not in ["individual", "organization", "employee"]:
        return None

    return target


# ==========================================================
# 1️⃣ GET Dynamic Fields (Fetch from SuperAdmin & save local)
# ==========================================================
class ProviderDynamicFieldsView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        target = normalize_target(request)
        if not target:
            return Response({"error": "Pass ?target=individual/organization/employee"}, status=400)

        # Fetch from SuperAdmin
        try:
            url = f"{SUPERADMIN_URL}?target={target}"
            res = requests.get(url, timeout=5)

            if res.status_code == 200:
                fields = res.json()

                # save to local
                for f in fields:
                    LocalFieldDefinition.objects.update_or_create(
                        id=f["id"],
                        defaults={
                            "target": f["target"],
                            "name": f["name"],
                            "label": f["label"],
                            "field_type": f["field_type"],
                            "is_required": f["is_required"],
                            "options": f.get("options", []),
                            "order": f.get("order", 0),
                            "help_text": f.get("help_text", "")
                        }
                    )

                return Response({"fields": fields}, status=200)

        except Exception as e:
            print("SuperAdmin unreachable:", e)

        # fallback local
        local_fields = LocalFieldDefinition.objects.filter(target=target)
        serialized = LocalFieldDefinitionSerializer(local_fields, many=True).data

        return Response({"fields": serialized}, status=200)


# ==========================================================
# 2️⃣ CREATE/UPDATE VALUES (Submit)
# ==========================================================
class ProviderFieldSubmitView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProviderSubmitFieldSerializer

    def post(self, request):
        auth_user_id = request.GET.get("user")
        if not auth_user_id:
            return Response({"error": "Pass ?user=<auth_user_id>"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "Verified user not found"}, status=400)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        saved_items, errors = [], []

        for item in serializer.validated_data:
            field_id = item["field_id"]
            value = item.get("value")
            metadata = item.get("metadata", {})

            if not LocalFieldDefinition.objects.filter(id=field_id).exists():
                errors.append({"field_id": field_id, "error": "Unknown field"})
                continue

            obj, created = ProviderFieldValue.objects.update_or_create(
                verified_user=verified,
                field_id=field_id,
                defaults={"value": value, "metadata": metadata},
            )

            saved_items.append({
                "field_id": field_id,
                "value": value,
                "saved": True,
                "created": created,
            })

        return Response({"saved": saved_items, "errors": errors}, status=200)


# ------------------------------
# GET ALL SAVED VALUES (READ)
# ------------------------------
class ProviderFieldValuesListView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        auth_user_id = request.GET.get("user")
        if not auth_user_id:
            return Response({"error": "Missing ?user=<auth_user_id>"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "Verified user not found"}, status=404)

        values = ProviderFieldValue.objects.filter(verified_user=verified)
        data = [{
            "field_id": v.field_id,
            "value": v.value,
            "metadata": v.metadata,
            "updated_at": v.updated_at
        } for v in values]

        return Response({"values": data}, status=200)


# ------------------------------
# GET SINGLE FIELD VALUE
# ------------------------------
class ProviderFieldValueDetailView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, field_id):
        auth_user_id = request.GET.get("user")
        if not auth_user_id:
            return Response({"error": "Missing ?user=<auth_user_id>"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "Verified user not found"}, status=404)

        try:
            obj = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
        except ProviderFieldValue.DoesNotExist:
            return Response({"error": "Field value not found"}, status=404)

        return Response({
            "field_id": obj.field_id,
            "value": obj.value,
            "metadata": obj.metadata,
            "updated_at": obj.updated_at
        }, status=200)


# ------------------------------
# UPDATE SINGLE FIELD VALUE
# ------------------------------
class ProviderFieldValueUpdateView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProviderSubmitFieldSerializer

    def put(self, request, field_id):
        auth_user_id = request.GET.get("user")
        if not auth_user_id:
            return Response({"error": "Missing ?user=<auth_user_id>"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "Verified user not found"}, status=404)

        try:
            obj = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
        except ProviderFieldValue.DoesNotExist:
            return Response({"error": "Field value not found"}, status=404)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        obj.value = serializer.validated_data.get("value")
        obj.metadata = serializer.validated_data.get("metadata", {})
        obj.save()

        return Response({
            "message": "Updated successfully",
            "field_id": obj.field_id,
            "value": obj.value,
            "metadata": obj.metadata
        }, status=200)


# ------------------------------
# DELETE SINGLE FIELD
# ------------------------------
class ProviderFieldValueDeleteView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def delete(self, request, field_id):
        auth_user_id = request.GET.get("user")
        if not auth_user_id:
            return Response({"error": "Missing ?user=<auth_user_id>"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
        except VerifiedUser.DoesNotExist:
            return Response({"error": "Verified user not found"}, status=404)

        try:
            obj = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
        except ProviderFieldValue.DoesNotExist:
            return Response({"error": "Field value not found"}, status=404)

        obj.delete()
        return Response({"message": "Deleted successfully"}, status=200)
