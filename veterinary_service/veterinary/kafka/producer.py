
import json
import logging
from kafka import KafkaProducer
from django.conf import settings

logger = logging.getLogger(__name__)

class VeterinaryProducer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VeterinaryProducer, cls).__new__(cls)
            cls._instance.producer = None
        return cls._instance

    def _get_producer(self):
        if self.producer is None:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=settings.KAFKA_BROKER_URL,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
            except Exception as e:
                logger.error(f"Failed to connect to Kafka: {e}")
                return None
        return self.producer

    def send_event(self, event_type, data, topic='veterinary_events'):
        producer = self._get_producer()
        if producer:
            try:
                message = {
                    'event_type': event_type,
                    'data': data,
                    'service': 'veterinary_service'
                }
                producer.send(topic, message)
                producer.flush()
                logger.info(f"Sent event {event_type} to {topic}")
            except Exception as e:
                logger.error(f"Failed to send event {event_type}: {e}")
        else:
            logger.warning(f"Kafka producer not available. Event {event_type} dropped.")

# Global instance
producer = VeterinaryProducer()
