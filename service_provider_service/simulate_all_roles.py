
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

def simulate_all_roles():
    print("🚀 Simulating Kafka Events for ALL Roles...")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9093",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return

    org_id = "7470623a-ee4b-4922-99f5-3ce2f17171d7"
    
    roles_to_test = [
        "receptionist",
        "vitals staff",
        "doctor",
        "lab tech",
        "pharmacy"
    ]
    
    topic = "service_provider_events"
    
    for role in roles_to_test:
        auth_user_id = str(uuid.uuid4())
        name = f"Test {role.title()}"
        
        event = {
            "service": "auth_service",
            "event_type": "USER_CREATED",
            "role": role, # Sending exact role name as expected from Auth Service
            "data": {
                "auth_user_id": auth_user_id,
                "organization_id": org_id,
                "full_name": name,
                "email": f"{role.replace(' ', '')}_{auth_user_id[:5]}@test.com",
                "phone_number": f"9{auth_user_id[:9]}", # Dummy phone
                "role": role,
                "created_by": str(uuid.uuid4())
            },
            "timestamp": int(time.time())
        }
        
        print(f"📦 Sending {role}...")
        producer.send(topic, value=event)
    
    producer.flush()
    print("✅ All events sent.")

if __name__ == "__main__":
    simulate_all_roles()
