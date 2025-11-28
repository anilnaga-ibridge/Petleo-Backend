

# # kafka/consumer.py

# import json
# import logging
# import threading
# import time
# from kafka import KafkaConsumer
# from django.conf import settings

# logger = logging.getLogger(__name__)


# class GlobalKafkaConsumer(threading.Thread):
#     """
#     One universal Kafka consumer for the entire provider-service.
#     Supports:
#     - Multiple topics
#     - Multiple event handlers
#     - Safe daemon thread
#     """

#     handlers = {}   # event_name → callback function

#     def __init__(self, topics: list, group_id: str):
#         super().__init__(daemon=True)
#         self.topics = topics
#         self.group_id = group_id

#     @classmethod
#     def register_handler(cls, event_name: str):
#         """Attach event handlers dynamically."""
#         def decorator(func):
#             cls.handlers[event_name] = func
#             return func
#         return decorator

#     def run(self):
#         consumer = KafkaConsumer(
#             *self.topics,
#             bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
#             auto_offset_reset="earliest",
#             enable_auto_commit=True,
#             group_id=self.group_id,
#             value_deserializer=lambda m: json.loads(m.decode("utf-8")),
#         )

#         logger.info(f"🚀 Kafka Consumer Started → {self.topics}")

#         for message in consumer:
#             try:
#                 event_name = message.value.get("event") or message.value.get("event_type")
#                 payload = message.value.get("payload") or message.value.get("data") or {}

#                 logger.info(f"📥 Received → {event_name}")

#                 handler = self.handlers.get(event_name)

#                 if handler:
#                     handler(payload)
#                 else:
#                     logger.warning(f"⚠ No handler for → {event_name}")

#             except Exception as e:
#                 logger.exception(f"❌ Error processing Kafka message: {e}")
#                 time.sleep(1)

import os
import json
import django
import logging
from kafka import KafkaConsumer
from django.db import transaction
from django.conf import settings

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser

# Logging
logger = logging.getLogger("service_provider_consumer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

logger.info("🚀 Starting Service Provider Kafka Consumer...")

# Kafka setup
consumer = KafkaConsumer(
    "individual_events",
    "organization_events",
    bootstrap_servers="localhost:9092",
    group_id="service-provider-group",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

logger.info("✅ Connected to Kafka broker.")
logger.info("📡 Listening to: individual_events, organization_events")

for message in consumer:
    try:
        event = message.value
        event_type = (event.get("event_type") or "").upper()
        data = event.get("data", {})
        role = event.get("role")

        logger.info(f"🔥 Received event: {event_type} | Role: {role} | Data: {data}")

        if not data or not data.get("auth_user_id"):
            logger.warning("⚠️ Missing auth_user_id. Skipping message.")
            continue

        auth_user_id = data["auth_user_id"]

        if event_type in ["USER_CREATED", "USER_VERIFIED"]:
            with transaction.atomic():
                user, created = VerifiedUser.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "full_name": data.get("full_name"),
                        "email": data.get("email"),
                        "phone_number": data.get("phone_number"),
                        "role": role or data.get("role"),
                        "permissions": data.get("permissions", []),
                    },
                )
                logger.info(f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser ({user.email})")

        elif event_type == "USER_UPDATED":
            updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
                full_name=data.get("full_name"),
                email=data.get("email"),
                phone_number=data.get("phone_number"),
                role=role or data.get("role"),
            )
            if updated:
                logger.info(f"🆙 VerifiedUser updated: {data.get('email')}")
            else:
                logger.warning(f"⚠️ No VerifiedUser found for update: {auth_user_id}")

        elif event_type == "USER_DELETED":
            deleted, _ = VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()
            if deleted > 0:
                logger.info(f"🗑️ VerifiedUser deleted successfully: ID={auth_user_id}")
            else:
                logger.warning(f"⚠️ No VerifiedUser found for deletion: ID={auth_user_id}")

        else:
            logger.warning(f"⚠️ Unknown event type '{event_type}' received.")

    except Exception as e:
        logger.exception(f"❌ Error processing message: {e}")
