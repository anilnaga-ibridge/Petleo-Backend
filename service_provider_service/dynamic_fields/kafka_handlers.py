from .models import LocalFieldDefinition
from kafka.consumer import GlobalKafkaConsumer
import logging

logger = logging.getLogger(__name__)


# ---------------------------
# CREATE / UPDATE Handler
# ---------------------------
@GlobalKafkaConsumer.register_handler("dynamic_field.created")
@GlobalKafkaConsumer.register_handler("dynamic_field.updated")
def handle_field_upsert(payload):
    field_id = payload.get("id")

    if not field_id:
        logger.error("❌ Missing field ID in payload")
        return

    obj, created = LocalFieldDefinition.objects.update_or_create(
        id=field_id,
        defaults={
            "target": payload.get("target"),
            "name": payload.get("name"),
            "label": payload.get("label"),
            "field_type": payload.get("field_type"),
            "is_required": payload.get("is_required", False),
            "options": payload.get("options", []),
            "order": payload.get("order", 0),
            "help_text": payload.get("help_text"),
            "created_at": payload.get("created_at"),
        }
    )

    logger.info(f"🟣 LocalFieldDefinition saved → {obj.id} (created={created})")


# ---------------------------
# DELETE Handler
# ---------------------------
@GlobalKafkaConsumer.register_handler("dynamic_field.deleted")
def handle_field_delete(payload):
    field_id = payload.get("id")
    LocalFieldDefinition.objects.filter(id=field_id).delete()
    logger.info(f"🗑️ LocalFieldDefinition deleted → {field_id}")
