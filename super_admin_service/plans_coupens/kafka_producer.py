# superadmin/kafka_producer.py

import json
import logging
import threading
import uuid
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
        producer.flush()  # 🔥 Optimization: Restored for critical sync reliability

        logger.info(
            f"[KAFKA] Published event '{event_name}' for user {payload.get('data', {}).get('auth_user_id')}"
        )

    except Exception as e:
        logger.exception(f"[KAFKA ERROR] Failed to publish event {event_name}: {e}")


# -------------------------------------------
#  Permission Updated Event
# -------------------------------------------
def publish_permissions_updated(auth_user_id: str, purchase_id: str, permissions_list: list, purchased_plan: dict, templates: dict = None, dynamic_capabilities: list = None, entitlement_source: str = 'BILLING', is_legacy_reconciled: bool = False):
    if templates:
        print(f"DEBUG: Kafka Producer sending templates: {len(templates.get('services', []))} services, {len(templates.get('categories', []))} categories")
    else:
        print("DEBUG: Kafka Producer sending NO templates")

    # Add extra metadata into templates for consumer discovery without breaking schema
    enriched_templates = templates or {}
    enriched_templates["entitlement_source"] = entitlement_source
    enriched_templates["is_legacy_reconciled"] = is_legacy_reconciled
    
    # [FIX] If this is a legacy reconciliation, pass the MR number for the read-model
    if is_legacy_reconciled:
        from .models import LegacyEntitlementRecovery
        recovery = LegacyEntitlementRecovery.objects.filter(purchased_plan_id=purchase_id).first()
        if recovery:
            enriched_templates["migration_record_no"] = recovery.migration_record_number

    payload = {
        "event_type": "provider.permissions.updated",
        "schema_version": "2.0",
        "event_id": str(uuid.uuid4()),
        "occurred_at": timezone.now().isoformat(),
        "timestamp": timezone.now().isoformat(), # Keep for backward compatibility
        "data": {
            "provider_id": str(auth_user_id),
            "auth_user_id": str(auth_user_id), # Matching both keys for consumer compatibility
            "purchase_id": str(purchase_id),
            "plan_id": str(purchased_plan.get('plan_id')),
            "capabilities": permissions_list,
            "purchased_plan": purchased_plan,
            "templates": enriched_templates,
            "dynamic_capabilities": dynamic_capabilities or [],
            "entitlement_source": entitlement_source,
            "is_legacy_reconciled": is_legacy_reconciled
        },
    }

    print(f"DEBUG: [KAFKA SEND] provider.permissions.updated | User: {auth_user_id} | Ver: 2.0 | Source: {entitlement_source}")
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

# -------------------------------------------
#  Plan Status Changed Event
# -------------------------------------------
def publish_plan_status_changed(plan_id: str, is_active: bool):
    payload = {
        "event_type": "plan.status.changed",
        "occurred_at": timezone.now().isoformat(),
        "data": {
            "plan_id": str(plan_id),
            "is_active": is_active,
        },
    }

    publish_permissions_event("plan.status.changed", payload)
