from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Provider, ProviderDocumentSubmission
from .serializers import ProviderSerializer, ProviderDocumentSubmissionSerializer
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

# For calling SuperAdmin service to fetch definitions
import requests
from django.conf import settings

SUPERADMIN_BASE = getattr(settings, "SUPERADMIN_BASE", "http://superadmin-service:8000/api/")

class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]  # or AllowAny for registration

    # optionally override create for custom logic
    # def create(...): ...

class ProviderDocumentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = ProviderDocumentSubmission.objects.all()
    serializer_class = ProviderDocumentSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # restrict by provider query param or user
        provider_id = self.request.query_params.get("provider_id")
        if provider_id:
            return self.queryset.filter(provider_id=provider_id)
        return self.queryset

    @action(detail=False, methods=["post"], url_path="submit")
    def submit_documents(self, request):
        """
        Accept a list of document submissions for a provider.
        Expected payload:
        {
           "provider": 1,
           "documents": [
               {"code":"aadhar_card", "file": <file> } OR {"code":"fullname","value":"Anil"}
           ]
        }
        """
        provider_id = request.data.get("provider")
        provider = get_object_or_404(Provider, pk=provider_id)
        documents = request.data.get("documents", [])
        created = []
        errors = []
        for item in documents:
            code = item.get("code")
            value = item.get("value")
            file_obj = item.get("file")  # file must be sent in multipart/form-data
            required = item.get("required", True)

            # upsert logic: if exists update, else create
            obj, created_flag = ProviderDocumentSubmission.objects.update_or_create(
                provider=provider, code=code,
                defaults={
                    "value": value,
                    "file": file_obj,
                    "required": required,
                    "status": "PENDING",
                    "remarks": "",
                }
            )
            created.append(obj)
        serializer = ProviderDocumentSubmissionSerializer(created, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="verify")
    def verify(self, request, pk=None):
        """
        Endpoint to let SuperAdmin change status on a submission.
        Expected body:
        { "status": "APPROVED", "remarks": "ok", "verified_at": "2025-11-28T12:00:00Z" }
        """
        submission = self.get_object()
        status_val = request.data.get("status")
        remarks = request.data.get("remarks", "")
        if status_val not in dict(ProviderDocumentSubmission.STATUS_CHOICES).keys():
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        submission.status = status_val
        submission.remarks = remarks
        submission.verified_at = timezone.now()
        submission.save()
        serializer = ProviderDocumentSubmissionSerializer(submission, context={"request": request})
        return Response(serializer.data)
