# kafka/producer.py

import json
import threading
import logging
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from django.conf import settings

logger = logging.getLogger(__name__)


class GlobalKafkaProducer:
    """
    Universal Kafka Producer Singleton.
    Use in ANY Django service.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls):
        """Return a global, shared Kafka producer instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        logger.info("🚀 Initializing GLOBAL Kafka Producer...")

                        cls._instance = KafkaProducer(
                            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                            client_id=getattr(settings, "SERVICE_NAME", "unknown_service"),
                            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                            acks="all",
                            retries=10,
                            linger_ms=5,
                            retry_backoff_ms=200,
                            reconnect_backoff_ms=500,
                            max_in_flight_requests_per_connection=1,
                        )
                        logger.info("✅ Kafka Producer Connected")
                    except Exception as e:
                        logger.warning(f"⚠️ Kafka unavailable: {e}")
                        return None
        return cls._instance


def publish_event(topic: str, event: str, payload: dict, service: str):
    """
    Generic Kafka publisher for ALL microservices.
    """

    message = {
        "event_type": event,
        "service": service,
        "data": payload,
    }

    try:
        producer = GlobalKafkaProducer.instance()
        
        if not producer:
            logger.warning(f"⚠️ Kafka not connected. Event '{event}' skipped.")
            return

        producer.send(topic, message)
        # producer.flush()  # 🔥 Optimization: Removed blocking flush

        logger.info(f"📤 Kafka Event SENT → topic={topic}, event={event}")
        logger.debug(f"Payload → {message}")

    except Exception as e:
        logger.error(f"❌ Kafka Publish Failed → {e}")
