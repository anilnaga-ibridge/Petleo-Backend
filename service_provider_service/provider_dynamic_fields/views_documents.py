



from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from provider_dynamic_fields.models import (
    LocalDocumentDefinition,
    ProviderDocument
)

from provider_dynamic_fields.serializers import (
    LocalDocumentDefinitionSerializer,
    ProviderDocumentSerializer
)

from service_provider.models import VerifiedUser


SUPERADMIN_DOCS_PUBLIC = "http://127.0.0.1:8003/api/superadmin/definitions/documents/public/"


def normalize_target(request):
    target = request.GET.get("target") or request.GET.get("role")
    if target:
        target = target.strip().lower()
    return target if target in ["individual", "organization", "employee"] else None


# =====================================================================
# 1) Fetch document definitions
# =====================================================================
class ProviderDocumentDefinitionsView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        target = normalize_target(request)
        if not target:
            return Response({"error": "Pass ?target="})

        local = LocalDocumentDefinition.objects.filter(target=target).order_by("order")
        serializer = LocalDocumentDefinitionSerializer(local, many=True)
        return Response({"definitions": serializer.data})


# =====================================================================
# 2) Upload document (ALWAYS single, force replace)
# =====================================================================
class ProviderDocumentUploadView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user_id = request.GET.get("user")
        if not user_id:
            return Response({"error": "Missing ?user"}, status=400)

        try:
            verified = VerifiedUser.objects.get(auth_user_id=user_id)
        except:
            return Response({"error": "Invalid user"}, status=404)

        if "file" not in request.FILES:
            return Response({"error": "Missing file"}, status=400)

        definition_id = request.data.get("definition_id")
        if not definition_id:
            return Response({"error": "Missing definition_id"}, status=400)

        try:
            doc_def = LocalDocumentDefinition.objects.get(id=definition_id)
        except:
            return Response({"error": "Invalid document definition"}, status=400)

        upload = request.FILES["file"]

        # Allowed MIME types validation
        if doc_def.allowed_types and upload.content_type not in doc_def.allowed_types:
            return Response({"error": "File type not allowed"}, status=400)

        # ❌ ALWAYS REMOVE OLD FIRST to enforce single document
        old_docs = ProviderDocument.objects.filter(
            verified_user=verified,
            definition_id=definition_id
        )
        for d in old_docs:
            if d.file:
                d.file.delete(save=False)
            d.delete()

        # Create new document
        pd = ProviderDocument.objects.create(
            verified_user=verified,
            definition_id=definition_id,
            file=upload,
            filename=upload.name,
            content_type=upload.content_type or "",
            size=upload.size,
        )

        # Publish Event
        from service_provider.kafka_producer import publish_document_uploaded
        publish_document_uploaded(
            provider_id=verified.auth_user_id,
            document_id=pd.id,
            definition_id=pd.definition_id,
            file_url=request.build_absolute_uri(pd.file.url),
            filename=pd.filename
        )

        ser = ProviderDocumentSerializer(pd, context={"request": request})
        return Response({"uploaded": ser.data}, status=201)


# =====================================================================
# 3) List uploaded documents
# =====================================================================
class ProviderDocumentListView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.GET.get("user")
        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
        except:
            return Response({"error": "Invalid user"}, status=404)

        docs = ProviderDocument.objects.filter(verified_user=verified)
        ser = ProviderDocumentSerializer(docs, many=True, context={"request": request})
        return Response({"documents": ser.data})


# =====================================================================
# 4) Get or Delete single document
# =====================================================================
class ProviderDocumentDetailView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        user = request.GET.get("user")
        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
            doc = ProviderDocument.objects.get(id=pk, verified_user=verified)
        except:
            return Response({"error": "Not found"}, status=404)

        ser = ProviderDocumentSerializer(doc, context={"request": request})
        return Response(ser.data)

    def delete(self, request, pk):
        user = request.GET.get("user")
        try:
            verified = VerifiedUser.objects.get(auth_user_id=user)
            doc = ProviderDocument.objects.get(id=pk, verified_user=verified)
        except:
            return Response({"error": "Not found"}, status=404)

        # Remove physical file safely
        if doc.file:
            doc.file.delete(save=False)

        doc.delete()

        return Response({"message": "Deleted successfully"})
