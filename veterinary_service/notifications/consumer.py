import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
from .service import NotificationService

logger = logging.getLogger(__name__)

class NotificationConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'veterinary_events',
            bootstrap_servers=settings.KAFKA_BROKER_URL,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='notification_service_group'
        )

    def start(self):
        logger.info("Starting Notification Consumer...")
        for message in self.consumer:
            try:
                event = message.value
                event_type = event.get('event_type')
                payload = event.get('data')
                
                if event_type and payload:
                    NotificationService.handle_event(event_type, payload)
            except Exception as e:
                logger.error(f"Error processing message: {e}")

# To run this:
# python manage.py runscript start_notification_consumer
# Or separate process.
