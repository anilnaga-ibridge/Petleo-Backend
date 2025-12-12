from django.test import TestCase
from unittest.mock import patch, MagicMock
from .models import ProviderFieldDefinition, ProviderDocumentDefinition

class DynamicFieldsSignalTest(TestCase):
    @patch("dynamic_fields.signals.publish_event")
    def test_field_definition_created(self, mock_publish):
        """Test that creating a field triggers a Kafka event."""
        field = ProviderFieldDefinition.objects.create(
            target="individual",
            name="test_field",
            label="Test Field",
            field_type="text"
        )
        
        mock_publish.assert_called_once()
        args, kwargs = mock_publish.call_args
        self.assertEqual(kwargs['topic'], "admin_events")
        self.assertEqual(kwargs['event'], "FIELD_DEFINITION_CREATED")
        self.assertEqual(kwargs['payload']['name'], "test_field")

    @patch("dynamic_fields.signals.publish_event")
    def test_field_definition_updated(self, mock_publish):
        """Test that updating a field triggers a Kafka event."""
        field = ProviderFieldDefinition.objects.create(
            target="individual",
            name="test_field",
            label="Test Field",
            field_type="text"
        )
        mock_publish.reset_mock()
        
        field.label = "Updated Label"
        field.save()
        
        mock_publish.assert_called_once()
        args, kwargs = mock_publish.call_args
        self.assertEqual(kwargs['event'], "FIELD_DEFINITION_UPDATED")
        self.assertEqual(kwargs['payload']['label'], "Updated Label")

    @patch("dynamic_fields.signals.publish_event")
    def test_field_definition_deleted(self, mock_publish):
        """Test that deleting a field triggers a Kafka event."""
        field = ProviderFieldDefinition.objects.create(
            target="individual",
            name="test_field",
            label="Test Field",
            field_type="text"
        )
        mock_publish.reset_mock()
        
        field_id = str(field.id)
        field.delete()
        
        mock_publish.assert_called_once()
        args, kwargs = mock_publish.call_args
        self.assertEqual(kwargs['event'], "FIELD_DEFINITION_DELETED")
        self.assertEqual(kwargs['payload']['id'], field_id)
