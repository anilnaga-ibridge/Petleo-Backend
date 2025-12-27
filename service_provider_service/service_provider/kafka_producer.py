import json
import logging
import threading
from kafka import KafkaProducer
from .kafka_config import KAFKA_BOOTSTRAP_SERVERS

logger = logging.getLogger(__name__)

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
                        logger.info("✅ Service Provider Kafka Producer Connected")
                    except Exception as e:
                        logger.warning(f"⚠️ Kafka unavailable: {e}")
                        return None
        return cls._instance

def get_kafka_producer():
    return GlobalKafkaProducer.instance()

def publish_document_uploaded(provider_id, document_id, file_url, filename):
    producer = get_kafka_producer()
    
    if not producer:
        logger.warning(f"⚠️ Kafka not connected. Document upload event for '{filename}' skipped.")
        return

    topic = "service_provider_events" 
    
    payload = {
        "event_type": "PROVIDER.DOCUMENT.UPLOADED",
        "role": "service_provider",
        "data": {
            "auth_user_id": str(provider_id),
            "provider_id": str(provider_id),
            "document_id": str(document_id),
            "file_url": file_url,
            "filename": filename
        }
    }
    
    try:
        producer.send(topic, payload)
        producer.flush()
        logger.info(f"📤 Published PROVIDER.DOCUMENT.UPLOADED for {filename}")
    except Exception as e:
        logger.error(f"❌ Failed to publish document upload event: {e}")

def publish_employee_updated(employee):
    producer = get_kafka_producer()
    if not producer:
        logger.warning(f"⚠️ Kafka not connected. Employee update for '{employee.auth_user_id}' skipped.")
        return

    topic = "service_provider_events"
    
    # Get Organization ID (VerifiedUser auth_id of the provider)
    try:
        org_id = str(employee.organization.verified_user.auth_user_id)
    except Exception:
        org_id = None

    payload = {
        "event_type": "EMPLOYEE_UPDATED",
        "role": "employee",
        "data": {
            "auth_user_id": str(employee.auth_user_id),
            "organization_id": org_id,
            "full_name": employee.full_name,
            "email": employee.email,
            "phone_number": employee.phone_number
        }
    }
    
    try:
        producer.send(topic, payload)
        producer.flush()
        logger.info(f"📤 Published EMPLOYEE_UPDATED for {employee.auth_user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to publish employee update event: {e}")

def publish_employee_deleted(auth_user_id):
    producer = get_kafka_producer()
    if not producer:
        logger.warning(f"⚠️ Kafka not connected. Employee deletion for '{auth_user_id}' skipped.")
        return

    topic = "service_provider_events"
    
    payload = {
        "event_type": "EMPLOYEE_DELETED",
        "role": "employee",
        "data": {
            "auth_user_id": str(auth_user_id)
        }
    }
    
    try:
        producer.send(topic, payload)
        producer.flush()
        logger.info(f"📤 Published EMPLOYEE_DELETED for {auth_user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to publish employee deletion event: {e}")
