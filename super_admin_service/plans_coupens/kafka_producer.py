# superadmin/kafka_producer.py

import json
import logging
import threading
from kafka import KafkaProducer
from django.utils import timezone

from .kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC_PERMISSIONS,
)

logger = logging.getLogger(__name__)


# -------------------------------------------
#  Create a reusable Kafka Producer instance
# -------------------------------------------
class GlobalKafkaProducer:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = KafkaProducer(
                            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                            retries=5,
                            linger_ms=5,
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Kafka unavailable: {e}")
                        return None
        return cls._instance

def get_kafka_producer():
    return GlobalKafkaProducer.instance()


# -------------------------------------------
#  Generic event publisher
# -------------------------------------------
def publish_permissions_event(event_name: str, payload: dict):
    producer = get_kafka_producer()
    
    if not producer:
        logger.warning(f"⚠️ Kafka not connected. Event '{event_name}' skipped.")
        return

    try:
        producer.send(KAFKA_TOPIC_PERMISSIONS, payload)
        producer.flush()

        logger.info(
            f"[KAFKA] Published event '{event_name}' for user {payload.get('data', {}).get('auth_user_id')}"
        )

    except Exception as e:
        logger.exception(f"[KAFKA ERROR] Failed to publish event {event_name}: {e}")


# -------------------------------------------
#  Permission Updated Event
# -------------------------------------------
def publish_permissions_updated(auth_user_id: str, purchase_id: str, permissions_list: list, purchased_plan: dict, templates: dict = None):
    if templates:
        print(f"DEBUG: Kafka Producer sending templates: {len(templates.get('services', []))} services, {len(templates.get('categories', []))} categories")
    else:
        print("DEBUG: Kafka Producer sending NO templates")

    payload = {
        "event_type": "provider.permissions.updated",
        "occurred_at": timezone.now().isoformat(),
        "data": {
            "auth_user_id": str(auth_user_id),
            "purchase_id": str(purchase_id),
            "permissions": permissions_list,
            "purchased_plan": purchased_plan,
            "templates": templates or {},
        },
    }

    publish_permissions_event("provider.permissions.updated", payload)


# -------------------------------------------
#  Permission Revoked Event (future use)
# -------------------------------------------
def publish_permissions_revoked(auth_user_id: str, purchase_id: str = None):
    payload = {
        "event_type": "provider.permissions.revoked",
        "occurred_at": timezone.now().isoformat(),
        "data": {
            "auth_user_id": str(auth_user_id),
            "purchase_id": str(purchase_id) if purchase_id else None,
        },
    }

    publish_permissions_event("provider.permissions.revoked", payload)
