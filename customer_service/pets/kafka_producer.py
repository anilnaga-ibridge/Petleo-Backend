import json
import logging
from kafka import KafkaProducer
from django.conf import settings

logger = logging.getLogger("pets_producer")

# Kafka Producer init
_producer = None

def get_producer():
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers="localhost:9093",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks='all',
                retries=5
            )
            logger.info("✅ Get Kafka Producer Success")
        except Exception as e:
            logger.error(f"❌ Get Kafka Producer Failed: {e}")
    return _producer

def publish_pet_event(event_type, pet_instance):
    """
    Publishes a pet event to Kafka.
    """
    producer = get_producer()
    if not producer:
        return

    payload = {
        "event_type": event_type.upper(),
        "data": {
            "id": str(pet_instance.id),
            "owner_auth_user_id": str(pet_instance.owner.auth_user_id),
            "name": pet_instance.name,
            "species": pet_instance.species,
            "breed": pet_instance.breed,
            "dob": str(pet_instance.dob) if pet_instance.dob else None,
            "gender": pet_instance.gender,
            "microchip_id": pet_instance.microchip_id,
            "avatar_url": pet_instance.avatar_url,
        }
    }

    try:
        producer.send("customer_events", payload)
        producer.flush()
        logger.info(f"📤 Published {event_type} for Pet {pet_instance.id}")
    except Exception as e:
        logger.error(f"❌ Failed to publish pet event: {e}")
