
# import os
# import json
# import django
# import logging
# import time
# from kafka import KafkaConsumer
# from django.db import transaction
# from service_provider.models import VerifiedUser
# from django.conf import settings

# # --- Django setup ---
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
# django.setup()



# # --- Logging setup ---
# logger = logging.getLogger("service_provider_consumer")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

# logger.info("🚀 Starting Service Provider Kafka Consumer...")
# logger.info(f"📁 Using database file: {settings.DATABASES['default']['NAME']}")

# # --- Kafka Consumer setup ---
# consumer = KafkaConsumer(
#     "individual_events",
#     "organization_events",
#     bootstrap_servers="localhost:9092",
#     group_id="service-provider-group",
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     value_deserializer=lambda v: json.loads(v.decode("utf-8")),
# )

# logger.info("✅ Connected to Kafka broker successfully.")
# logger.info("📡 Listening to topics: individual_events, organization_events...")

# # --- Event processing loop ---
# for message in consumer:
#     try:
#         event = message.value
#         logger.info(f"📨 Received event: {event}")

#         event_type = event.get("event_type")
#         data = event.get("data", {})

#         if not data:
#             logger.warning("⚠️ No data in event, skipping")
#             continue

#         auth_user_id = data.get("auth_user_id")
#         if not auth_user_id:
#             logger.warning("⚠️ No auth_user_id in data, skipping")
#             continue

#         if event_type in ["USER_CREATED", "USER_VERIFIED"]:
#             try:
#                 with transaction.atomic():
#                     user, created = VerifiedUser.objects.update_or_create(
#                         auth_user_id=auth_user_id,
#                         defaults={
#                             "full_name": data.get("full_name", ""),
#                             "email": data.get("email", ""),
#                             "phone_number": data.get("phone_number", ""),
#                             "role": data.get("role", ""),
#                             "permissions": data.get("permissions", []),
#                         },
#                     )
#                     logger.info(
#                         f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser: {user.email}"
#                     )

#             except Exception as db_err:
#                 logger.exception(f"❌ Database error processing {event_type}: {db_err}")

#         else:
#             logger.warning(f"⚠️ Unknown event type: {event_type}")
#             logger.info(f"Event data: {data}")

#     except Exception as e:
#         logger.exception(f"❌ Error processing message: {e}")



import os
import json
import django
import logging
from kafka import KafkaConsumer

# --- Django setup (IMPORTANT: Do this before model imports) ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from django.db import transaction
from django.conf import settings
from service_provider.models import VerifiedUser

# --- Logging setup ---
logger = logging.getLogger("service_provider_consumer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger.info("🚀 Starting Service Provider Kafka Consumer...")
logger.info(f"📁 Using database file: {settings.DATABASES['default']['NAME']}")

# --- Kafka Consumer setup ---
consumer = KafkaConsumer(
    "individual_events",
    "organization_events",
    bootstrap_servers="localhost:9092",
    group_id="service-provider-group",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

logger.info("✅ Connected to Kafka broker successfully.")
logger.info("📡 Listening to topics: individual_events, organization_events...")

for message in consumer:
    try:
        event = message.value
        logger.info(f"📨 Received event: {event}")

        event_type = event.get("event_type")
        data = event.get("data", {})

        if not data:
            logger.warning("⚠️ No data in event, skipping")
            continue

        auth_user_id = data.get("auth_user_id")
        if not auth_user_id:
            logger.warning("⚠️ No auth_user_id in data, skipping")
            continue

        if event_type in ["USER_CREATED", "USER_VERIFIED"]:
            try:
                with transaction.atomic():
                    user, created = VerifiedUser.objects.update_or_create(
                        auth_user_id=auth_user_id,
                        defaults={
                            "full_name": data.get("full_name", ""),
                            "email": data.get("email", ""),
                            "phone_number": data.get("phone_number", ""),
                            "role": data.get("role", ""),
                            "permissions": data.get("permissions", []),
                        },
                    )
                    logger.info(
                        f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser: {user.email}"
                    )

            except Exception as db_err:
                logger.exception(f"❌ Database error processing {event_type}: {db_err}")

        else:
            logger.warning(f"⚠️ Unknown event type: {event_type}")
            logger.info(f"Event data: {data}")

    except Exception as e:
        logger.exception(f"❌ Error processing message: {e}")
