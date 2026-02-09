
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from admin_core.permissions import IsSuperAdmin
from django.shortcuts import get_object_or_404
from .models import ProviderDocumentVerification
from .serializers import ProviderDocumentVerificationSerializer
from kafka_client.kafka_producer import publish_event

TOPIC = "admin_events"
SERVICE = "super_admin_service"

class ProviderDocumentVerificationViewSet(viewsets.ModelViewSet):
    queryset = ProviderDocumentVerification.objects.all()
    serializer_class = ProviderDocumentVerificationSerializer
    permission_classes = [IsSuperAdmin]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = ProviderDocumentVerification.objects.all()
        
        status_param = self.request.query_params.get("status")
        auth_user_id = self.request.query_params.get("auth_user_id")
        
        if status_param:
            qs = qs.filter(status=status_param)
        if auth_user_id:
            qs = qs.filter(auth_user_id=auth_user_id)
            
        return qs

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """
        Approve or Reject a document.
        Body: { "status": "approved" | "rejected", "rejection_reason": "..." }
        """
        document = self.get_object()
        new_status = request.data.get("status")
        reason = request.data.get("rejection_reason", "")

        if new_status not in ["approved", "rejected"]:
            return Response({"error": "Invalid status. Use 'approved' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)

        document.status = new_status
        document.rejection_reason = reason if new_status == "rejected" else ""
        document.save()

        # Publish Kafka Event
        payload = {
            "document_id": str(document.document_id),
            "auth_user_id": str(document.auth_user_id),
            "status": new_status,
            "rejection_reason": document.rejection_reason
        }

        publish_event(
            topic=TOPIC,
            event="admin.document.verified",
            payload=payload,
            service=SERVICE
        )

        # ✅ Check if all documents for this user are now approved
        all_docs = ProviderDocumentVerification.objects.filter(auth_user_id=document.auth_user_id)
        if all_docs.exists() and not all_docs.exclude(status='approved').exists():
            # Trigger USER_VERIFIED
            verify_payload = {
                "auth_user_id": str(document.auth_user_id),
                "status": "ACTIVE",
                "is_verified": True
            }
            publish_event(
                topic=TOPIC,
                event="USER_VERIFIED",
                payload=verify_payload,
                service=SERVICE
            )
            print(f"📡 Published USER_VERIFIED for {document.auth_user_id}")

        return Response(ProviderDocumentVerificationSerializer(document).data)
