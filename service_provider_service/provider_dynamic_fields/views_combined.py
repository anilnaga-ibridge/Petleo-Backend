# # provider_dynamic_fields/views_combined.py
# from rest_framework import generics, status
# from rest_framework.permissions import AllowAny
# from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser

# from provider_dynamic_fields.models import (
#     LocalFieldDefinition,
#     LocalDocumentDefinition,
#     ProviderFieldValue,
#     ProviderDocument
# )
# from provider_dynamic_fields.serializers import ProviderProfileSerializer, ProviderDocumentSerializer
# from service_provider.models import VerifiedUser

# import json


# def normalize_target(request):
#     """Normalize target from query params."""
#     target = request.GET.get("target") or request.GET.get("role")
#     if target:
#         target = target.strip().lower()
#     return target if target in ["individual", "organization", "employee"] else None


# class ProviderProfileView(generics.GenericAPIView):
#     """
#     GET: Fetch dynamic fields + uploaded documents + requested documents
#     POST: Save/update field values + upload/update documents
#     """
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser, FormParser]

#     def get_verified_user(self, auth_user_id):
#         if not auth_user_id:
#             return None, Response({"error": "Missing ?user="}, status=400)
#         try:
#             verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
#             return verified, None
#         except VerifiedUser.DoesNotExist:
#             return None, Response({"error": "User not found"}, status=404)

#     # -------------------------------------------------------
#     # GET PROFILE
#     # -------------------------------------------------------
#     def get(self, request):
#         auth_user_id = request.GET.get("user")
#         verified, error_response = self.get_verified_user(auth_user_id)
#         if error_response:
#             return error_response

#         target = normalize_target(request) or getattr(verified, "provider_type", "individual")

#         fields_qs = LocalFieldDefinition.objects.filter(target=target).order_by("order")
#         docs_qs = ProviderDocument.objects.filter(verified_user=verified)
#         requested_docs_qs = LocalDocumentDefinition.objects.filter(target=target).order_by("order")

#         # Populate existing field values
#         fields_data = []
#         for f in fields_qs:
#             try:
#                 saved_value = ProviderFieldValue.objects.get(verified_user=verified, field_id=f.id)
#                 value = saved_value.value
#                 metadata = saved_value.metadata or {}
#             except ProviderFieldValue.DoesNotExist:
#                 value = None
#                 metadata = {}

#             fields_data.append({
#                 "id": str(f.id),
#                 "name": f.name,
#                 "label": f.label,
#                 "field_type": f.field_type,
#                 "is_required": f.is_required,
#                 "options": f.options,
#                 "help_text": f.help_text,
#                 "value": value,
#                 "metadata": metadata
#             })

#         # Use serializer to include file_url / size / content_type
#         uploaded_docs_serialized = ProviderDocumentSerializer(docs_qs, many=True, context={"request": request}).data

#         requested_documents = [
#             {
#                 "id": str(d.id),
#                 "key": d.key,
#                 "label": d.label,
#                 "allow_multiple": d.allow_multiple,
#                 "allowed_types": d.allowed_types,
#                 "help_text": d.help_text,
#             } for d in requested_docs_qs
#         ]

#         serializer = ProviderProfileSerializer({
#             "fields": fields_data,
#             "uploaded_documents": uploaded_docs_serialized,
#             "requested_documents": requested_documents
#         })

#         return Response(serializer.data)

#     # -------------------------------------------------------
#     # POST (SAVE / UPDATE FIELDS + DOCUMENTS)
#     # -------------------------------------------------------
#     def post(self, request):
#         auth_user_id = request.GET.get("user")
#         verified, error_response = self.get_verified_user(auth_user_id)
#         if error_response:
#             return error_response

#         data = request.data

#         # ------------------ Save / Update Field Values ------------------
#         fields_data = data.get("fields", "[]")
#         try:
#             fields_data = json.loads(fields_data)
#         except json.JSONDecodeError:
#             return Response({"error": "Invalid fields JSON"}, status=400)

#         saved_fields = []
#         for item in fields_data:
#             field_id = item.get("field_id")
#             value = item.get("value")
#             metadata = item.get("metadata", {})

#             try:
#                 LocalFieldDefinition.objects.get(id=field_id)
#             except LocalFieldDefinition.DoesNotExist:
#                 continue

#             obj, created = ProviderFieldValue.objects.update_or_create(
#                 verified_user=verified,
#                 field_id=field_id,
#                 defaults={"value": value, "metadata": metadata}
#             )

#             saved_fields.append({
#                 "field_id": field_id,
#                 "value": value,
#                 "new": created
#             })

#         # ------------------ Save / Update Documents ------------------
#         uploaded_files = []

#         # request.FILES.lists() gives (field_name, list_of_files)
#         for definition_id, file_list in request.FILES.lists():
#             # definition_id should be the LocalDocumentDefinition id (string)
#             try:
#                 doc_def = LocalDocumentDefinition.objects.get(id=definition_id)
#             except LocalDocumentDefinition.DoesNotExist:
#                 # skip unknown field names
#                 continue

#             # If not allow_multiple, delete existing and use only first file
#             if not doc_def.allow_multiple:
#                 ProviderDocument.objects.filter(
#                     verified_user=verified,
#                     definition_id=definition_id
#                 ).delete()
#                 file_list = file_list[:1]

#             for f in file_list:
#                 doc = ProviderDocument.objects.create(
#                     verified_user=verified,
#                     definition_id=definition_id,
#                     file=f,
#                     filename=f.name,
#                     content_type=getattr(f, "content_type", None) or '',
#                     size=getattr(f, "size", None) or (f.size if hasattr(f, "size") else 0),
#                 )

#                 uploaded_files.append({
#                     "id": str(doc.id),
#                     "definition_id": str(doc.definition_id),
#                     "filename": doc.filename,
#                     "file_url": request.build_absolute_uri(doc.file.url),
#                     "size": doc.size,
#                     "content_type": doc.content_type,
#                     "uploaded_at": doc.uploaded_at,
#                 })

#         return Response({
#             "saved_fields": saved_fields,
#             "uploaded_files": uploaded_files
#         }, status=status.HTTP_201_CREATED)
# provider_dynamic_fields/views_combined.py
# from rest_framework import generics, status
# from rest_framework.permissions import AllowAny
# from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser

# from provider_dynamic_fields.models import (
#     LocalFieldDefinition,
#     LocalDocumentDefinition,
#     ProviderFieldValue,
#     ProviderDocument
# )
# from provider_dynamic_fields.serializers import ProviderDocumentSerializer
# from service_provider.models import VerifiedUser

# import json


# def normalize_target(request):
#     target = request.GET.get("target") or request.GET.get("role")
#     if target:
#         target = target.strip().lower()
#     return target if target in ["individual", "organization", "employee"] else None


# class ProviderProfileView(generics.GenericAPIView):
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser, FormParser]

#     def get_verified_user(self, auth_user_id):
#         if not auth_user_id:
#             return None, Response({"error": "Missing ?user="}, status=400)
#         try:
#             verified = VerifiedUser.objects.get(auth_user_id=auth_user_id)
#             return verified, None
#         except VerifiedUser.DoesNotExist:
#             return None, Response({"error": "User not found"}, status=404)

#     def get(self, request):
#         auth_user_id = request.GET.get("user")
#         verified, error_response = self.get_verified_user(auth_user_id)
#         if error_response:
#             return error_response

#         target = normalize_target(request) or getattr(verified, "provider_type", "individual")

#         fields_qs = LocalFieldDefinition.objects.filter(target=target).order_by("order")
#         docs_qs = ProviderDocument.objects.filter(verified_user=verified)
#         requested_docs_qs = LocalDocumentDefinition.objects.filter(target=target).order_by("order")

#         # prepare fields with saved values
#         fields_data = []
#         for f in fields_qs:
#             try:
#                 saved_value = ProviderFieldValue.objects.get(verified_user=verified, field_id=f.id)
#             except ProviderFieldValue.DoesNotExist:
#                 saved_value = None

#             if saved_value and saved_value.file:
#                 # file-type saved as file
#                 value = None
#                 metadata = {
#                     "name": saved_value.file.name.split("/")[-1],
#                     "size": saved_value.file.size,
#                     "content_type": saved_value.metadata.get("content_type") if saved_value.metadata else None,
#                     "file_url": request.build_absolute_uri(saved_value.file.url)
#                 }
#             else:
#                 value = saved_value.value if saved_value else None
#                 metadata = saved_value.metadata if saved_value else {}

#             fields_data.append({
#                 "id": str(f.id),
#                 "name": f.name,
#                 "label": f.label,
#                 "field_type": f.field_type,
#                 "is_required": f.is_required,
#                 "options": f.options,
#                 "help_text": f.help_text,
#                 "value": value,
#                 "metadata": metadata
#             })

#         uploaded_docs_serialized = ProviderDocumentSerializer(docs_qs, many=True, context={"request": request}).data

#         requested_documents = [
#             {
#                 "id": str(d.id),
#                 "key": d.key,
#                 "label": d.label,
#                 "allow_multiple": d.allow_multiple,
#                 "allowed_types": d.allowed_types,
#                 "help_text": d.help_text,
#             } for d in requested_docs_qs
#         ]

#         return Response({
#             "fields": fields_data,
#             "uploaded_documents": uploaded_docs_serialized,
#             "requested_documents": requested_documents
#         })

#     def post(self, request):
#         auth_user_id = request.GET.get("user")
#         verified, error_response = self.get_verified_user(auth_user_id)
#         if error_response:
#             return error_response

#         # parse fields JSON (stringified by frontend)
#         fields_data = request.data.get("fields", "[]")
#         try:
#             fields_data = json.loads(fields_data)
#         except json.JSONDecodeError:
#             return Response({"error": "Invalid fields JSON"}, status=400)

#         saved_fields = []
#         # Update non-file fields (value + metadata)
#         for item in fields_data:
#             field_id = item.get("field_id")
#             value = item.get("value")
#             metadata = item.get("metadata", {})

#             # make sure the field exists
#             try:
#                 LocalFieldDefinition.objects.get(id=field_id)
#             except LocalFieldDefinition.DoesNotExist:
#                 continue

#             # if field_type != 'file' -> save to ProviderFieldValue.value
#             ProviderFieldValue.objects.update_or_create(
#                 verified_user=verified,
#                 field_id=field_id,
#                 defaults={
#                     "value": value,
#                     # do not touch file here
#                     "metadata": metadata
#                 }
#             )
#             saved_fields.append({"field_id": field_id, "value": value})

#         uploaded_profile_files = []
#         uploaded_files = []

#         # Process request.FILES:
#         # key could be a field_id (profile field) or a document definition id (requested-docs)
#         field_ids_in_payload = {str(x.get("field_id")) for x in fields_data if x.get("field_id")}

#         for key, file_list in request.FILES.lists():
#             # file_list is a list of UploadedFile (even if single)
#             # If key matches a field_id -> save into ProviderFieldValue.file
#             if key in field_ids_in_payload:
#                 # treat as profile field file(s) - usually single
#                 for f in file_list:
#                     obj, created = ProviderFieldValue.objects.update_or_create(
#                         verified_user=verified,
#                         field_id=key,
#                         defaults={
#                             "file": f,
#                             "value": {"filename": f.name},
#                             "metadata": {"content_type": getattr(f, "content_type", ""), "size": getattr(f, "size", 0)}
#                         }
#                     )
#                     uploaded_profile_files.append({
#                         "field_id": key,
#                         "filename": f.name,
#                         "file_url": request.build_absolute_uri(obj.file.url),
#                         "size": getattr(f, "size", 0),
#                         "content_type": getattr(f, "content_type", "")
#                     })
#                 continue

#             # Otherwise try to match a LocalDocumentDefinition (requested-docs)
#             try:
#                 doc_def = LocalDocumentDefinition.objects.get(id=key)
#             except LocalDocumentDefinition.DoesNotExist:
#                 # unknown key - ignore
#                 continue

#             # If not allow_multiple -> delete existing
#             if not doc_def.allow_multiple:
#                 ProviderDocument.objects.filter(verified_user=verified, definition_id=key).delete()

#             for f in file_list:
#                 doc = ProviderDocument.objects.create(
#                     verified_user=verified,
#                     definition_id=key,
#                     file=f,
#                     filename=f.name,
#                     content_type=getattr(f, "content_type", "") or "",
#                     size=getattr(f, "size", 0)
#                 )
#                 uploaded_files.append({
#                     "id": str(doc.id),
#                     "definition_id": str(doc.definition_id),
#                     "filename": doc.filename,
#                     "file_url": request.build_absolute_uri(doc.file.url),
#                     "size": doc.size,
#                     "content_type": doc.content_type,
#                     "uploaded_at": doc.uploaded_at,
#                 })

#         return Response({
#             "saved_fields": saved_fields,
#             "uploaded_profile_files": uploaded_profile_files,
#             "uploaded_files": uploaded_files
#         }, status=status.HTTP_201_CREATED)
# provider_dynamic_fields/views_combined.py

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

        return Response({
            "fields": fields_data,
            "uploaded_documents": uploaded_documents,
            "requested_documents": requested_documents
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
