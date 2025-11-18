from kafka import KafkaProducer

try:
    print("⏳ Trying to connect to Kafka...")
    p = KafkaProducer(bootstrap_servers="localhost:9092")
    print("✅ SUCCESS: Connected to Kafka")
except Exception as e:
    print("❌ FAILED:", e)
