import json
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable, KafkaError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection(broker_url):
    print(f"\nTesting connection to: {broker_url}")
    try:
        producer = KafkaProducer(
            bootstrap_servers=[broker_url],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
            request_timeout_ms=5000,
            api_version_auto_timeout_ms=5000
        )
        print(f"✅ SUCCESS: Connected to {broker_url}")
        print(f"   Bootstrap Connected: {producer.bootstrap_connected()}")
        
        # Try sending a message
        future = producer.send('test_topic', {'key': 'value'})
        result = future.get(timeout=10)
        print(f"✅ SUCCESS: Message sent to {result.topic} partition {result.partition} offset {result.offset}")
        
        producer.close()
        return True
    except NoBrokersAvailable:
        print(f"❌ FAILED: NoBrokersAvailable for {broker_url}")
    except Exception as e:
        print(f"❌ FAILED: Error connecting to {broker_url}: {e}")
    return False

if __name__ == "__main__":
    print("--- Starting Kafka Connection Test ---")
    
    # Test 1: localhost:9093
    test_connection("localhost:9093")
    
    # Test 2: 127.0.0.1:9093
    test_connection("127.0.0.1:9093")
    
    # Test 3: 0.0.0.0:9093
    test_connection("0.0.0.0:9093")
    
    print("\n--- Test Complete ---")
