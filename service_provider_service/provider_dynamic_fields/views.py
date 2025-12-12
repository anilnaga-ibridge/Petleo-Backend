

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
