import json
import logging
import os
from kafka import KafkaProducer
from django.conf import settings

logger = logging.getLogger("bookings_producer")

# Kafka Producer init
_producer = None

def get_producer():
    global _producer
    if _producer is None:
        try:
            broker_url = os.environ.get("KAFKA_BROKER_URL", "localhost:9093")
            _producer = KafkaProducer(
                bootstrap_servers=broker_url,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks='all',
                retries=5
            )
            logger.info(f"✅ Kafka Producer initialized for Bookings at {broker_url}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka Producer: {e}")
    return _producer

def publish_booking_event(event_type, booking_instance):
    """
    Publishes a booking event to Kafka.
    """
    producer = get_producer()
    if not producer:
        logger.warning(f"⚠️ Kafka producer not available, skipping {event_type} for booking {booking_instance.id}")
        return

    # Use the first item for breadcrumb data
    first_item = booking_instance.items.first()
    if not first_item:
        logger.warning(f"⚠️ Booking {booking_instance.id} has no items, skipping event.")
        return

    service_snap = first_item.service_snapshot or {}
    pet_snap = first_item.pet_snapshot or {}
    # Use header snapshot or item snapshot
    owner_snap = booking_instance.owner_snapshot or first_item.owner_snapshot or {}
    
    payload = {
        "event_type": event_type.upper(),
        "booking_id": str(booking_instance.id),
        "data": {
            "booking_id": str(booking_instance.id),
            "owner_auth_id": str(booking_instance.owner_id),
            "owner_name": owner_snap.get('full_name') or owner_snap.get('name') or "User",
            "pet_name": pet_snap.get('name') or "Pet",
            "provider_id": str(first_item.provider_id),
            "assigned_employee_id": str(first_item.assigned_employee_id) if first_item.assigned_employee_id else None,
            "service_name": service_snap.get('service_name', 'General Service'),
            "selected_time": first_item.selected_time.isoformat(),
            "status": booking_instance.status,
            "total_price": str(booking_instance.total_price),
        }
    }

    try:
        producer.send("booking_events", payload)
        producer.flush()
        logger.info(f"📤 Published {event_type} for Booking {booking_instance.id} to 'booking_events'")
    except Exception as e:
        logger.error(f"❌ Failed to publish booking event {event_type}: {e}")
