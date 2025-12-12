import os
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093").split(",")
KAFKA_TOPIC_DYNAMIC_FIELDS = os.getenv("KAFKA_TOPIC_DYNAMIC_FIELDS", "provider.dynamic_fields.v1")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "serviceprovider-dynamic-fields")
