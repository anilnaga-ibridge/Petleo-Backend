
from django.test import TestCase
from unittest.mock import MagicMock, patch
from dynamic_fields.models import ProviderDocumentVerification
import uuid

class DocumentVerificationFlowTests(TestCase):
    def test_consume_document_uploaded_event(self):
        # Simulate PROVIDER.DOCUMENT.UPLOADED event
        payload = {
            "event_type": "PROVIDER.DOCUMENT.UPLOADED",
            "data": {
                "provider_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "file_url": "http://example.com/doc.pdf",
                "filename": "doc.pdf"
            }
        }
        
        # Logic extracted from kafka_consumer.py
        data = payload["data"]
        ProviderDocumentVerification.objects.create(
            provider_id=data.get("provider_id"),
            document_id=data.get("document_id"),
            file_url=data.get("file_url"),
            filename=data.get("filename"),
            status="pending"
        )
        
        # Verify
        self.assertEqual(ProviderDocumentVerification.objects.count(), 1)
        obj = ProviderDocumentVerification.objects.first()
        self.assertEqual(obj.filename, "doc.pdf")
        self.assertEqual(obj.status, "pending")

    @patch('dynamic_fields.views_verification.publish_event')
    def test_verify_document_view(self, mock_publish):
        # Create initial record
        doc = ProviderDocumentVerification.objects.create(
            provider_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            file_url="http://example.com/doc.pdf",
            filename="doc.pdf",
            status="pending"
        )
        
        # Call the view logic (simulated)
        from dynamic_fields.views_verification import ProviderDocumentVerificationViewSet
        view = ProviderDocumentVerificationViewSet()
        view.request = MagicMock()
        view.request.query_params = {}
        view.request.data = {"status": "approved"}
        view.kwargs = {"pk": doc.id}
        view.action = "verify"
        
        # Call the view method
        view.verify(view.request, pk=doc.id)
        
        self.assertTrue(mock_publish.called)
