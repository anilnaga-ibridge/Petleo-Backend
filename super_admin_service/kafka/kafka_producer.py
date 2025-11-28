# kafka/producer.py

import json
import threading
import logging
from kafka import KafkaProducer
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
        return cls._instance


def publish_event(topic: str, event: str, payload: dict, service: str):
    """
    Generic Kafka publisher for ALL microservices.
    """

    message = {
        "event": event,
        "service": service,
        "payload": payload,
    }

    try:
        producer = GlobalKafkaProducer.instance()
        producer.send(topic, message)
        producer.flush()

        logger.info(f"📤 Kafka Event SENT → topic={topic}, event={event}")
        logger.debug(f"Payload → {message}")

    except Exception as e:
        logger.error(f"❌ Kafka Publish Failed → {e}")
