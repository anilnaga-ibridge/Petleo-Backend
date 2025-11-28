# plans_coupons/kafka_config.py

import os

# You can override these via environment variables if needed.
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092").split(",")

# Topic where SuperAdmin publishes plan permissions
KAFKA_TOPIC_PERMISSIONS = os.getenv("KAFKA_TOPIC_PERMISSIONS", "provider.permissions.v1")
