

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
from service_provider.kafka_producer import publish_user_profile_updated
import json


def normalize_target(request):
    """Normalize provider type."""
    target = request.GET.get("target") or request.GET.get("role")
    if target:
        target = target.strip().lower()
    return target if target in ["individual", "organization", "employee", "superadmin"] else None


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
    # -------------------------------------------------------
    # GET PROFILE
    # -------------------------------------------------------
    def get(self, request):
        user_id = request.GET.get("user")
        verified, error = self.get_verified_user(user_id)
        if error:
            return error

        target = normalize_target(request) or getattr(verified, "provider_type", "individual")

        # 1. Fetch Field Definitions from Local DB (Synced)
        from .models import LocalFieldDefinition, LocalDocumentDefinition
        
        field_definitions_qs = LocalFieldDefinition.objects.filter(target=target).order_by('order')
        field_definitions = []
        for fd in field_definitions_qs:
            field_definitions.append({
                "id": str(fd.id),
                "name": fd.name,
                "label": fd.label,
                "field_type": fd.field_type,
                "is_required": fd.is_required,
                "options": fd.options,
                "order": fd.order,
                "help_text": fd.help_text
            })

        # 2. Fetch Document Definitions from Local DB (Synced)
        doc_definitions_qs = LocalDocumentDefinition.objects.filter(target=target).order_by('order')
        doc_definitions = []
        for dd in doc_definitions_qs:
            doc_definitions.append({
                "id": str(dd.id),
                "key": dd.key,
                "label": dd.label,
                "is_required": dd.is_required,
                "allow_multiple": dd.allow_multiple,
                "allowed_types": dd.allowed_types,
                "order": dd.order,
                "help_text": dd.help_text
            })

        # 3. Fetch Uploaded Documents
        uploaded_docs_qs = ProviderDocument.objects.filter(verified_user=verified)
        uploaded_documents = ProviderDocumentSerializer(uploaded_docs_qs, many=True, context={"request": request}).data

        # 4. Merge Fields with Values
        fields_data = []
        for field in field_definitions:
            field_id = field.get('id')
            
            try:
                saved_value = ProviderFieldValue.objects.get(verified_user=verified, field_id=field_id)
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

                # 🔥 SOURCE OF TRUTH: Use VerifiedUser for basic fields
                field_name = field.get("name")
                if field_name in ["first_name", "last_name", "email", "phone_number", "country", "language"]:
                    full_name = verified.full_name or ""
                    parts = full_name.split(" ", 1)
                    first = parts[0] if parts else ""
                    last = parts[1] if len(parts) > 1 else ""

                    if field_name == "first_name":
                        value = first
                    elif field_name == "last_name":
                        value = last
                    elif field_name == "email":
                        value = verified.email
                    elif field_name == "phone_number":
                        value = verified.phone_number
                    elif field_name == "country":
                        value = value or "India"
                    elif field_name == "language":
                        value = value or "English"

            fields_data.append({
                **field,
                "value": value,
                "metadata": metadata,
            })

        # 5. Format Document Definitions for Response
        requested_documents = doc_definitions # Already formatted above

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
        user_id = request.GET.get("user") or request.data.get("user") or request.data.get("auth_user_id")
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

        # -----------------------------------------------
        # 🔥 SYNC BASIC FIELDS back to VerifiedUser
        # -----------------------------------------------
        user_updated = False
        full_name = verified.full_name or ""
        parts = full_name.split(" ", 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""

        for item in fields_data:
            field_id = item.get("field_id")
            value = item.get("value")
            try:
                field_def = LocalFieldDefinition.objects.get(id=field_id)
            except:
                continue
            
            field_name = field_def.name
            if field_name == "first_name":
                first = value
                user_updated = True
            elif field_name == "last_name":
                last = value
                user_updated = True
            elif field_name == "email":
                verified.email = value
                user_updated = True
            elif field_name == "phone_number":
                verified.phone_number = value
                user_updated = True

        if user_updated:
            verified.full_name = f"{first} {last}".strip()
            verified.save()
            
            # Publish to Kafka for Auth Service sync
            publish_user_profile_updated(
                auth_user_id=verified.auth_user_id,
                full_name=verified.full_name,
                email=verified.email,
                phone_number=verified.phone_number
            )

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

                # 🔥 SYNC BACK to dynamic field "profile_image"
                try:
                    target = getattr(verified, "provider_type", "individual")
                    field_def = LocalFieldDefinition.objects.filter(target=target, name="profile_image").first()
                    if field_def:
                        ProviderFieldValue.objects.update_or_create(
                            verified_user=verified,
                            field_id=field_def.id,
                            defaults={
                                "file": upload_file,
                                "value": {"filename": upload_file.name},
                                "metadata": {
                                    "content_type": getattr(upload_file, "content_type", ""),
                                    "size": upload_file.size
                                }
                            }
                        )
                except Exception as e:
                    print(f"Error syncing avatar to profile_image field: {e}")
                
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

                # 🔥 SYNC TO ServiceProvider.avatar if this is the "profile_image" field
                try:
                    field_def = LocalFieldDefinition.objects.get(id=key)
                    if field_def.name == "profile_image":
                        from service_provider.models import ServiceProvider
                        provider, _ = ServiceProvider.objects.get_or_create(verified_user=verified)
                        provider.avatar = upload_file
                        provider.save()
                except Exception as e:
                    print(f"Error syncing profile_image to avatar: {e}")

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
                    definition_id=doc.definition_id,
                    file_url=request.build_absolute_uri(doc.file.url),
                    filename=doc.filename
                )

                uploaded_docs.append({
                    "id": str(doc.id),
                    "definition_id": str(doc.definition_id),
                    "filename": doc.filename,
                    "file_url": request.build_absolute_uri(doc.file.url),
                })

        # Fetch Avatar URL for immediate frontend refresh
        avatar_url = None
        try:
            from service_provider.models import ServiceProvider
            provider = ServiceProvider.objects.filter(verified_user=verified).first()
            if provider and provider.avatar:
                avatar_url = request.build_absolute_uri(provider.avatar.url)
        except Exception:
            pass

        return Response({
            "message": "Profile updated successfully",
            "saved_fields": saved_fields,
            "uploaded_profile_files": uploaded_profile_files,
            "uploaded_files": uploaded_docs,
            "avatar": avatar_url,
            "user_profile": {
                "fullName": verified.full_name,
                "email": verified.email,
                "phoneNumber": verified.phone_number,
                "avatar": avatar_url
            }
        }, status=status.HTTP_201_CREATED)
