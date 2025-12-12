from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ProviderFieldDefinition, ProviderDocumentDefinition
from kafka_client.kafka_producer import publish_event
from .serializers import ProviderFieldDefinitionSerializer, ProviderDocumentDefinitionSerializer

TOPIC = "admin_events"
SERVICE = "super_admin_service"

# ==========================
# FIELD DEFINITION SIGNALS
# ==========================
@receiver(post_save, sender=ProviderFieldDefinition)
def field_definition_changed(sender, instance, created, **kwargs):
    event_type = "FIELD_DEFINITION_CREATED" if created else "FIELD_DEFINITION_UPDATED"
    serializer = ProviderFieldDefinitionSerializer(instance)
    
    publish_event(
        topic=TOPIC,
        event=event_type,
        payload=serializer.data,
        service=SERVICE
    )

@receiver(post_delete, sender=ProviderFieldDefinition)
def field_definition_deleted(sender, instance, **kwargs):
    publish_event(
        topic=TOPIC,
        event="FIELD_DEFINITION_DELETED",
        payload={"id": str(instance.id), "target": instance.target},
        service=SERVICE
    )

# ==========================
# DOCUMENT DEFINITION SIGNALS
# ==========================
@receiver(post_save, sender=ProviderDocumentDefinition)
def document_definition_changed(sender, instance, created, **kwargs):
    event_type = "DOCUMENT_DEFINITION_CREATED" if created else "DOCUMENT_DEFINITION_UPDATED"
    serializer = ProviderDocumentDefinitionSerializer(instance)

    publish_event(
        topic=TOPIC,
        event=event_type,
        payload=serializer.data,
        service=SERVICE
    )

@receiver(post_delete, sender=ProviderDocumentDefinition)
def document_definition_deleted(sender, instance, **kwargs):
    publish_event(
        topic=TOPIC,
        event="DOCUMENT_DEFINITION_DELETED",
        payload={"id": str(instance.id), "target": instance.target},
        service=SERVICE
    )
