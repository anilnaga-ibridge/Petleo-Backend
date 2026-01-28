import json
import os
from kafka import KafkaProducer

def trigger():
    # Read the payload from the file I saved earlier
    with open("payload.json", "r") as f:
        content = f.read().strip()
    
    # Strip prefix "SA Response: 201 - "
    if "SA Response: 201 - " in content:
        json_str = content.split("SA Response: 201 - ")[1]
    else:
        json_str = content

    import datetime
    
    data = json.loads(json_str)
    
    # Construct the proper event payload expected by the consumer
    # The payload.json contains the inner parts (permissions, templates, purchased_plan)
    # merged with some extra keys.
    
    kafka_payload = {
        "event_type": "PROVIDER.PERMISSIONS.UPDATED",
        "occurred_at": datetime.datetime.now().isoformat(),
        "data": {
            "auth_user_id": "4ce26186-7b1c-4b82-949c-e69e9431be68",
            "purchase_id": data.get("purchase_id"),
            "permissions": data.get("permissions"),
            "purchased_plan": data.get("purchased_plan"),
            "templates": data.get("templates"),
            "dynamic_capabilities": data.get("dynamic_capabilities", [])
        }
    }

    print(f"Payload prepared for user {kafka_payload['data']['auth_user_id']}")

    producer = KafkaProducer(
        bootstrap_servers=['localhost:9093'],
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        key_serializer=lambda x: x.encode('utf-8')
    )

    # Topic name from consumer config
    topic = 'admin_events'
    event_key = 'PROVIDER.PERMISSIONS.UPDATED'

    producer.send(topic, key=event_key, value=kafka_payload)
    producer.flush()
    print(f"✅ Event {event_key} sent to {topic}")

if __name__ == "__main__":
    trigger()
