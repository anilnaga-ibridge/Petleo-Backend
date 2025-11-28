# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from .models import ProviderFieldDefinition
# from .serializers import ProviderFieldDefinitionSerializer
# from .kafka_producer import publish_definition_event

# @receiver(post_save, sender=ProviderFieldDefinition)
# def on_definition_saved(sender, instance, created, **kwargs):
#     action = "created" if created else "updated"
#     data = ProviderFieldDefinitionSerializer(instance).data
#     publish_definition_event(action, data)

# @receiver(post_delete, sender=ProviderFieldDefinition)
# def on_definition_deleted(sender, instance, **kwargs):
#     data = {"id": str(instance.id)}
#     publish_definition_event("deleted", data)
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from .models import ProviderFieldDefinition
from .serializers import ProviderFieldDefinitionSerializer
from kafka.producer import publish_event


@receiver(post_save, sender=ProviderFieldDefinition)
def on_definition_saved(sender, instance, created, **kwargs):
    event = "dynamic_field.created" if created else "dynamic_field.updated"
    payload = ProviderFieldDefinitionSerializer(instance).data

    publish_event(
        topic=settings.KAFKA_TOPIC_DYNAMIC_FIELDS,
        event=event,
        payload=payload,
        service="superadmin"
    )


@receiver(post_delete, sender=ProviderFieldDefinition)
def on_definition_deleted(sender, instance, **kwargs):
    publish_event(
        topic=settings.KAFKA_TOPIC_DYNAMIC_FIELDS,
        event="dynamic_field.deleted",
        payload={"id": str(instance.id)},
        service="superadmin"
    )
