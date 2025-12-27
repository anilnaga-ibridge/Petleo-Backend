import json
import uuid
import time
from kafka import KafkaProducer

def test_kafka_real():
    print("--- Testing Real Kafka Transmission ---")
    
    producer = KafkaProducer(
        bootstrap_servers="localhost:9093",
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    
    # Use nagaanil292's ID (which we know exists and has a profile)
    # Auth ID: 1431597c-72be-4565-a051-9cd8a9dea66c
    org_id = "1431597c-72be-4565-a051-9cd8a9dea66c"
    new_emp_id = str(uuid.uuid4())
    
    payload = {
        "service": "test_script",
        "event_type": "USER_CREATED",
        "role": "employee",
        "data": {
            "auth_user_id": new_emp_id,
            "full_name": "Real Kafka Employee",
            "email": f"real.kafka.{new_emp_id[:8]}@example.com",
            "phone_number": "+1112223333",
            "organization_id": org_id,
            "created_by": org_id
        },
        "timestamp": int(time.time())
    }
    
    print(f"Sending payload to 'service_provider_events': {json.dumps(payload, indent=2)}")
    
    producer.send("service_provider_events", value=payload)
    producer.flush()
    print("✅ Message sent.")

if __name__ == "__main__":
    test_kafka_real()
