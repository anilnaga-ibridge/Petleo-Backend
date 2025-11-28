# superadmin/kafka_producer.py

import json
import logging
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
def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=5,
        linger_ms=5,
    )


# -------------------------------------------
#  Generic event publisher
# -------------------------------------------
def publish_permissions_event(event_name: str, payload: dict):
    producer = get_kafka_producer()

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
def publish_permissions_updated(auth_user_id: str, purchase_id: str, permissions_list: list, purchased_plan: dict):
    payload = {
        "event": "provider.permissions.updated",
        "occurred_at": timezone.now().isoformat(),
        "data": {
            "auth_user_id": str(auth_user_id),
            "purchase_id": str(purchase_id),
            "permissions": permissions_list,
            "purchased_plan": purchased_plan,
        },
    }

    publish_permissions_event("provider.permissions.updated", payload)


# -------------------------------------------
#  Permission Revoked Event (future use)
# -------------------------------------------
def publish_permissions_revoked(auth_user_id: str, purchase_id: str = None):
    payload = {
        "event": "provider.permissions.revoked",
        "occurred_at": timezone.now().isoformat(),
        "data": {
            "auth_user_id": str(auth_user_id),
            "purchase_id": str(purchase_id) if purchase_id else None,
        },
    }

    publish_permissions_event("provider.permissions.revoked", payload)
