import json
import logging
from kafka import KafkaProducer
from django.conf import settings

logger = logging.getLogger("bookings_producer")

# Kafka Producer init
_producer = None

def get_producer():
    global _producer
    if _producer is None:
        try:
            # We use the same configuration as other producers in the system
            _producer = KafkaProducer(
                bootstrap_servers="localhost:9093",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks='all',
                retries=5
            )
            logger.info("✅ Kafka Producer initialized for Bookings")
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

    # Assuming a single-item booking for now as per current frontend flow
    first_item = booking_instance.items.first()
    if not first_item:
        logger.warning(f"⚠️ Booking {booking_instance.id} has no items, skipping event.")
        return

    snapshot = first_item.service_snapshot or {}
    
    payload = {
        "event_type": event_type.upper(),
        "booking_id": str(booking_instance.id),
        "data": {
            "booking_id": str(booking_instance.id),
            "owner_auth_id": str(booking_instance.owner.auth_user_id),
            "owner_name": booking_instance.owner.full_name,
            "pet_name": first_item.pet.name,
            "provider_auth_id": str(first_item.provider_auth_id),
            "assigned_employee_id": str(first_item.assigned_employee_id) if first_item.assigned_employee_id else None,
            "service_name": snapshot.get('service_name', 'General Service'),
            "selected_time": first_item.selected_time.isoformat(),
            "status": booking_instance.status,
            "total_price": str(booking_instance.total_price),
        }
    }

    try:
        producer.send("booking_events", payload)
        # producer.flush()  # 🔥 Optimization: Removed blocking flush
        logger.info(f"📤 Published {event_type} for Booking {booking_instance.id} to 'booking_events'")
    except Exception as e:
        logger.error(f"❌ Failed to publish booking event {event_type}: {e}")
