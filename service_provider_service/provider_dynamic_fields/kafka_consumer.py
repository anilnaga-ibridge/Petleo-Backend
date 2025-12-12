# import json
# import logging
import logging
# import time
# from kafka import KafkaConsumer
# from django.conf import settings
# import django
# import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger("kafka").setLevel(logging.CRITICAL)

# If you want to run this standalone: set DJANGO_SETTINGS_MODULE env var before importing models
logger = logging.getLogger(__name__)

# Minimal consumer loop — idempotent upsert for definitions
# def run_consumer():
#     from .kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_DYNAMIC_FIELDS, KAFKA_CONSUMER_GROUP
#     from .models import LocalFieldDefinition

    consumer = None
    while not consumer:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC_DYNAMIC_FIELDS,
                bootstrap_servers=getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP_SERVERS),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=getattr(settings, "KAFKA_CONSUMER_GROUP", KAFKA_CONSUMER_GROUP),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
        except Exception as e:
            logger.warning(f"⚠️ Kafka unavailable: {e}")
            logger.info("🔁 Retrying in 5 seconds...")
            time.sleep(5)

#     logger.info("DynamicFields consumer started, listening for events...")
#     for msg in consumer:
#         try:
#             payload = msg.value
#             event = payload.get("event")
#             data = payload.get("data", {})
#             logger.info("Received event %s", event)

#             if event.endswith(".created") or event.endswith(".updated"):
#                 fld_id = data.get("id")
#                 # upsert
#                 obj, created = LocalFieldDefinition.objects.update_or_create(
#                     id=fld_id,
#                     defaults={
#                         "target": data.get("target"),
#                         "name": data.get("name"),
#                         "label": data.get("label"),
#                         "field_type": data.get("field_type"),
#                         "is_required": data.get("is_required", False),
#                         "options": data.get("options", []),
#                         "order": data.get("order", 0),
#                         "help_text": data.get("help_text"),
#                         "created_at": data.get("created_at") or None,
#                     }
#                 )
#                 logger.info("Upserted LocalFieldDefinition %s (created=%s)", fld_id, created)
#             elif event.endswith(".deleted"):
#                 fld_id = data.get("id")
#                 LocalFieldDefinition.objects.filter(id=fld_id).delete()
#                 logger.info("Deleted LocalFieldDefinition %s", fld_id)
#         except Exception as e:
#             logger.exception("Error processing dynamic field event: %s", e)
#             time.sleep(1)
