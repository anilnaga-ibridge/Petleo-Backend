import json
from kafka import KafkaProducer
import uuid

producer = KafkaProducer(
    bootstrap_servers="localhost:9093",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

topic = "admin_events"
payload = {
    "event_type": "ADMIN.DOCUMENT.VERIFIED",
    "service": "manual_test",
    "role": "super_admin",
    "data": {
        "document_id": str(uuid.uuid4()),
        "auth_user_id": str(uuid.uuid4()),
        "status": "approved",
        "rejection_reason": ""
    }
}

print(f"Sending test event to {topic}...")
producer.send(topic, payload)
producer.flush()
print("Event sent!")
