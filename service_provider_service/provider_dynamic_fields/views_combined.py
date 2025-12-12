

from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from provider_dynamic_fields.models import (
    LocalFieldDefinition,
    LocalDocumentDefinition,
    ProviderFieldValue,
    ProviderDocument
)

from provider_dynamic_fields.serializers import ProviderDocumentSerializer
from service_provider.models import VerifiedUser
import json


def normalize_target(request):
    """Normalize provider type."""
    target = request.GET.get("target") or request.GET.get("role")
    if target:
        target = target.strip().lower()
    return target if target in ["individual", "organization", "employee"] else None


class ProviderProfileView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    # -------------------------------------------------------
    # Helper
    # -------------------------------------------------------
    def get_verified_user(self, user_id):
        if not user_id:
            return None, Response({"error": "Missing ?user"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=user_id)
            return verified, None
        except VerifiedUser.DoesNotExist:
            return None, Response({"error": "User not found"}, status=404)

    # -------------------------------------------------------
    # GET PROFILE
    # -------------------------------------------------------
    def get(self, request):
        user_id = request.GET.get("user")
        verified, error = self.get_verified_user(user_id)
        if error:
            return error

        target = normalize_target(request) or getattr(verified, "provider_type", "individual")

        fields_qs = LocalFieldDefinition.objects.filter(target=target).order_by("order")
        requested_docs_qs = LocalDocumentDefinition.objects.filter(target=target).order_by("order")
        uploaded_docs_qs = ProviderDocument.objects.filter(verified_user=verified)

        uploaded_documents = ProviderDocumentSerializer(uploaded_docs_qs, many=True, context={"request": request}).data

        fields_data = []
        for field in fields_qs:
            try:
                saved_value = ProviderFieldValue.objects.get(verified_user=verified, field_id=field.id)
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

            fields_data.append({
                "id": str(field.id),
                "name": field.name,
                "label": field.label,
                "field_type": field.field_type,
                "is_required": field.is_required,
                "options": field.options,
                "help_text": field.help_text,
                "value": value,
                "metadata": metadata,
            })

        requested_documents = [
            {
                "id": str(doc.id),
                "key": doc.key,
                "label": doc.label,
                "allow_multiple": doc.allow_multiple,
                "allowed_types": doc.allowed_types,
                "help_text": doc.help_text,
            }
            for doc in requested_docs_qs
        ]

        # Fetch Avatar from ServiceProvider
        avatar_url = None
        if hasattr(verified, 'provider_profile') and verified.provider_profile.avatar:
            avatar_url = request.build_absolute_uri(verified.provider_profile.avatar.url)

        return Response({
            "fields": fields_data,
            "uploaded_documents": uploaded_documents,
            "requested_documents": requested_documents,
            "avatar": avatar_url
        })

    # -------------------------------------------------------
    # POST PROFILE
    # -------------------------------------------------------
    def post(self, request):
        user_id = request.GET.get("user")
        verified, error = self.get_verified_user(user_id)
        if error:
            return error

        # -----------------------------------------------
        # 1) Parse FIELD JSON
        # -----------------------------------------------
        try:
            fields_data = json.loads(request.data.get("fields", "[]"))
        except json.JSONDecodeError:
            return Response({"error": "Invalid fields JSON"}, status=400)

        saved_fields = []

        for item in fields_data:
            field_id = item.get("field_id")
            value = item.get("value")
            metadata = item.get("metadata", {})

            if not field_id:
                continue

            try:
                field_def = LocalFieldDefinition.objects.get(id=field_id)
            except LocalFieldDefinition.DoesNotExist:
                continue

            if field_def.field_type == "file":
                continue

            ProviderFieldValue.objects.update_or_create(
                verified_user=verified,
                field_id=field_id,
                defaults={"value": value, "metadata": metadata}
            )

            saved_fields.append({"field_id": field_id, "value": value})

        field_ids_set = set(str(f["field_id"]) for f in fields_data)

        uploaded_profile_files = []
        uploaded_docs = []

        # -----------------------------------------------
        # 2) FILE UPLOADS
        # -----------------------------------------------
        for key, files in request.FILES.lists():

            # ============================
            # AVATAR UPLOAD
            # ============================
            if key == 'avatar':
                from service_provider.models import ServiceProvider
                upload_file = files[0]
                provider, _ = ServiceProvider.objects.get_or_create(verified_user=verified)
                provider.avatar = upload_file
                provider.save()
                continue

            # ============================
            # PROFILE FIELD FILES
            # ============================
            if key in field_ids_set:
                upload_file = files[0]

                obj, _ = ProviderFieldValue.objects.update_or_create(
                    verified_user=verified,
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

                uploaded_profile_files.append({
                    "field_id": key,
                    "filename": upload_file.name,
                    "size": upload_file.size,
                    "content_type": getattr(upload_file, "content_type", ""),
                    "file_url": request.build_absolute_uri(obj.file.url),
                })
                continue

            # ============================
            # REQUESTED DOCUMENT FILES
            # ============================
            try:
                doc_def = LocalDocumentDefinition.objects.get(id=key)
            except LocalDocumentDefinition.DoesNotExist:
                continue

            # ❗ ALWAYS enforce single file for requested docs
            # delete both file from disk + db record
            old_docs = ProviderDocument.objects.filter(verified_user=verified, definition_id=key)

            for old in old_docs:
                if old.file:
                    old.file.delete(save=False)

            old_docs.delete()

            # keep only the first uploaded file
            files = [files[0]]

            for f in files:
                doc = ProviderDocument.objects.create(
                    verified_user=verified,
                    definition_id=key,
                    file=f,
                    filename=f.name,
                    content_type=getattr(f, "content_type", ""),
                    size=f.size
                )

                # 🔥 Publish Event
                from service_provider.kafka_producer import publish_document_uploaded
                publish_document_uploaded(
                    provider_id=verified.auth_user_id,
                    document_id=doc.id,
                    file_url=request.build_absolute_uri(doc.file.url),
                    filename=doc.filename
                )

                uploaded_docs.append({
                    "id": str(doc.id),
                    "definition_id": str(doc.definition_id),
                    "filename": doc.filename,
                    "file_url": request.build_absolute_uri(doc.file.url),
                })

        return Response({
            "saved_fields": saved_fields,
            "uploaded_profile_files": uploaded_profile_files,
            "uploaded_files": uploaded_docs
        }, status=status.HTTP_201_CREATED)
