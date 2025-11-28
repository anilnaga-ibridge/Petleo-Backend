# import json
# import threading
# from kafka import KafkaProducer
# from django.conf import settings
# import logging

# logger = logging.getLogger(__name__)

# # Load config
# from config.kafka_config import (
#     KAFKA_BOOTSTRAP_SERVERS,
#     KAFKA_TOPIC_DYNAMIC_FIELDS
# )


# # -------------------------------------
# # SINGLETON KAFKA PRODUCER
# # -------------------------------------
# class KafkaProducerSingleton:
#     _instance = None
#     _lock = threading.Lock()

#     @classmethod
#     def get_producer(cls):
#         if cls._instance is None:
#             with cls._lock:
#                 if cls._instance is None:
#                     logger.info("🚀 Initializing Kafka Producer for Dynamic Fields...")

#                     cls._instance = KafkaProducer(
#                         bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
#                         value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#                         retries=5,
#                         acks="all",
#                         max_in_flight_requests_per_connection=1,
#                         linger_ms=5,
#                     )
#         return cls._instance


# # -------------------------------------
# # PUBLISH EVENT TO KAFKA
# # -------------------------------------
# def publish_definition_event(action, payload):
#     """
#     action: created | updated | deleted
#     payload: ProviderFieldDefinition serialized data
#     """

#     message = {
#         "event": action,
#         "model": "ProviderFieldDefinition",
#         "service": "super_admin_service",
#         "payload": payload,
#     }

#     try:
#         producer = KafkaProducerSingleton.get_producer()

#         producer.send(KAFKA_TOPIC_DYNAMIC_FIELDS, message)
#         producer.flush()

#         logger.info(f"📤 Kafka Event Published → {action.upper()} : {message}")

#     except Exception as e:
#         logger.error(f"❌ Kafka Publish Error → {e}")
