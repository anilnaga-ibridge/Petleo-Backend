# service_provider/kafka_config.py

import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092").split(",")
KAFKA_TOPIC_PERMISSIONS = os.getenv("KAFKA_TOPIC_PERMISSIONS", "provider.permissions.v1")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "serviceprovider-permissions-consumer")
