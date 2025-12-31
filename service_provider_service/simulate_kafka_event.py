
import os
import django
import sys
import json
import uuid
import time

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from kafka import KafkaProducer
from django.conf import settings

def simulate_event():
    print("🚀 Simulating Kafka Event for Receptionist...")
    
    # Create a dummy producer to send to localhost:9093
    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9093",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return

    # Data for a new receptionist
    auth_user_id = str(uuid.uuid4())
    org_id = "5d560f6b-a1cb-4025-b7bb-87ef212f8a1c" # Using an existing Org ID from logs
    
    event = {
        "service": "auth_service",
        "event_type": "USER_CREATED",
        "role": "receptionist",
        "data": {
            "auth_user_id": auth_user_id,
            "organization_id": org_id,
            "full_name": "Simulated Receptionist",
            "email": f"receptionist_{auth_user_id[:8]}@example.com",
            "phone_number": "1234567890",
            "role": "receptionist",
            "created_by": str(uuid.uuid4())
        },
        "timestamp": int(time.time())
    }
    
    topic = "service_provider_events"
    
    print(f"📦 Sending event to '{topic}':")
    print(json.dumps(event, indent=2))
    
    producer.send(topic, value=event)
    producer.flush()
    print("✅ Event sent.")

if __name__ == "__main__":
    simulate_event()
