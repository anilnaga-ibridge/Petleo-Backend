
# import os
# import json
# import django
# import logging
# from kafka import KafkaConsumer

# # --- Django setup ---
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import VerifiedUser  # ✅ your model

# # --- Logging setup ---
# logger = logging.getLogger("super_admin_consumer")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

# logger.info("🚀 Starting SuperAdmin Kafka Consumer...")

# # --- Kafka Consumer setup ---
# consumer = KafkaConsumer(
#     "service_events",                          # ✅ topic name
#     bootstrap_servers="host.docker.internal:9092",
#     group_id="superadmin-service-group",
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     value_deserializer=lambda v: json.loads(v.decode("utf-8")),
# )

# logger.info("✅ Connected to Kafka broker successfully.")
# logger.info("📡 Listening to topic 'service_events'...")

# # --- Event processing ---
# for message in consumer:
#     event = message.value
#     logger.info(f"📨 Received event: {event}")

#     event_type = event.get("event_type")
#     data = event.get("data", {})

#     try:
#         if event_type == "USER_CREATED":
#             logger.info("🧩 Processing USER_CREATED event...")

#             user, created = VerifiedUser.objects.get_or_create(
#                 auth_user_id=data["auth_user_id"],
#                 defaults={
#                     "full_name": data.get("full_name"),
#                     "email": data.get("email"),
#                     "phone_number": data.get("phone_number"),
#                     "role": data.get("role"),
#                     "permissions": data.get("permissions", []),
#                 },
#             )

#             if created:
#                 logger.info(f"✅ New VerifiedUser created: {user.email}")
#             else:
#                 logger.info(f"ℹ️ VerifiedUser already exists: {user.email}")

#         elif event_type == "USER_VERIFIED":
#             logger.info("🔐 Processing USER_VERIFIED event...")

#             updated = VerifiedUser.objects.filter(
#                 email=data.get("email")
#             ).update(
#                 full_name=data.get("full_name"),
#                 role=data.get("role"),
#                 permissions=data.get("permissions", []),
#             )

#             if updated:
#                 logger.info(f"✅ VerifiedUser '{data['email']}' marked as verified.")
#             else:
#                 logger.warning(f"⚠️ VerifiedUser not found for email: {data.get('email')}")

#         else:
#             logger.warning(f"⚠️ Unknown event type received: {event_type}")

#     except Exception as e:
#         logger.error(f"❌ Error while processing {event_type}: {e}", exc_info=True)


# import os
# import json
# import django
# import logging
# from kafka import KafkaConsumer

# # --- Django setup ---
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import VerifiedUser  # ✅ your model

# # --- Logging setup ---
# logger = logging.getLogger("super_admin_consumer")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

# logger.info("🚀 Starting SuperAdmin Kafka Consumer...")

# # --- Kafka Consumer setup ---
# consumer = KafkaConsumer(
#     "service_events",                          # ✅ topic name
#     bootstrap_servers="host.docker.internal:9092",
#     group_id="superadmin-service-group",
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     value_deserializer=lambda v: json.loads(v.decode("utf-8")),
# )

# logger.info("✅ Connected to Kafka broker successfully.")
# logger.info("📡 Listening to topic 'service_events'...")

# # --- Event processing ---
# for message in consumer:
#     event = message.value
#     logger.info(f"📨 Received event: {event}")

#     event_type = event.get("event_type")
#     data = event.get("data", {})

#     try:
#         if event_type == "USER_CREATED":
#             logger.info("🧩 Processing USER_CREATED event...")

#             user, created = VerifiedUser.objects.get_or_create(
#                 auth_user_id=data["auth_user_id"],
#                 defaults={
#                     "full_name": data.get("full_name"),
#                     "email": data.get("email"),
#                     "phone_number": data.get("phone_number"),
#                     "role": data.get("role"),
#                     "permissions": data.get("permissions", []),
#                 },
#             )

#             if created:
#                 logger.info(f"✅ New VerifiedUser created: {user.email}")
#             else:
#                 logger.info(f"ℹ️ VerifiedUser already exists: {user.email}")

#         elif event_type == "USER_VERIFIED":
#             logger.info("🔐 Processing USER_VERIFIED event...")

#             updated = VerifiedUser.objects.filter(
#                 email=data.get("email")
#             ).update(
#                 full_name=data.get("full_name"),
#                 role=data.get("role"),
#                 permissions=data.get("permissions", []),
#             )

#             if updated:
#                 logger.info(f"✅ VerifiedUser '{data['email']}' marked as verified.")
#             else:
#                 logger.warning(f"⚠️ VerifiedUser not found for email: {data.get('email')}")

#         else:
#             logger.warning(f"⚠️ Unknown event type received: {event_type}")

#     except Exception as e:
#         logger.error(f"❌ Error while processing {event_type}: {e}", exc_info=True)


# import os
# import json
# import django
# import logging
# from kafka import KafkaConsumer
# from django.db import transaction

# # --- Django setup ---
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import VerifiedUser

# # --- Logging setup ---
# logger = logging.getLogger("super_admin_consumer")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

# logger.info("🚀 Starting SuperAdmin Kafka Consumer...")

# # --- Kafka Consumer setup ---
# consumer = KafkaConsumer(
#     "admin_events",  # updated topic for super_admin role
#     "service_events",  # fallback/default topic
#     bootstrap_servers="host.docker.internal:9092",
#     group_id="superadmin-service-group",
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     value_deserializer=lambda v: json.loads(v.decode("utf-8")),
# )

# logger.info("✅ Connected to Kafka broker successfully.")
# logger.info("📡 Listening to topics: admin_events, service_events")

# for message in consumer:
#     try:
#         event = message.value
#         event_type = event.get("event_type")
#         data = event.get("data", {})
#         role = event.get("role")

#         logger.info(f"📨 Received {event_type} event for role '{role}': {data}")

#         if not data or not data.get("auth_user_id"):
#             logger.warning("⚠️ Missing data or auth_user_id. Skipping...")
#             continue

#         auth_user_id = data["auth_user_id"]

#         if event_type == "USER_CREATED":
#             with transaction.atomic():
#                 user, created = VerifiedUser.objects.update_or_create(
#                     auth_user_id=auth_user_id,
#                     defaults={
#                         "full_name": data.get("full_name"),
#                         "email": data.get("email"),
#                         "phone_number": data.get("phone_number"),
#                         "role": role or data.get("role"),
#                         "permissions": data.get("permissions", []),
#                     },
#                 )
#                 logger.info(f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser ({user.email})")

#         elif event_type == "USER_UPDATED":
#             updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
#                 full_name=data.get("full_name"),
#                 email=data.get("email"),
#                 phone_number=data.get("phone_number"),
#                 role=role or data.get("role"),
#             )
#             if updated:
#                 logger.info(f"🆙 VerifiedUser updated: {data.get('email')}")
#             else:
#                 logger.warning(f"⚠️ VerifiedUser not found for ID: {auth_user_id}")

#         elif event_type == "USER_DELETED":
#             deleted = VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()
#             if deleted[0] > 0:
#                 logger.info(f"🗑️ VerifiedUser deleted: ID={auth_user_id}")
#             else:
#                 logger.warning(f"⚠️ No VerifiedUser found for deletion: ID={auth_user_id}")

#         else:
#             logger.warning(f"⚠️ Unknown event type received: {event_type}")

#     except Exception as e:
#         logger.exception(f"❌ Error while processing {event_type}: {e}")
# import os
# import json
# import django
# import logging
# from kafka import KafkaConsumer
# from django.db import transaction
# from django.conf import settings

# # --- Django setup ---
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import VerifiedUser

# # --- Logging setup ---
# logger = logging.getLogger("super_admin_consumer")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

# logger.info("🚀 Starting SuperAdmin Kafka Consumer...")
# logger.info(f"📁 Using DB: {settings.DATABASES['default']['NAME']}")

# # --- Kafka Consumer setup ---
# consumer = KafkaConsumer(
#     "admin_events",       # ✅ Topic for admin/superadmin events
#     "service_events",     # ✅ Optional fallback topic
#     bootstrap_servers="localhost:9092",
#     group_id="superadmin-service-group",
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     value_deserializer=lambda v: json.loads(v.decode("utf-8")),
# )

# logger.info("✅ Connected to Kafka broker successfully.")
# logger.info("📡 Listening to topics: admin_events, service_events")

# # --- Event processing loop ---
# for message in consumer:
#     try:
#         event = message.value
#         event_type = event.get("event_type")
#         data = event.get("data", {})
#         role = event.get("role")

#         logger.info(f"📨 Received {event_type} event for role='{role}': {data}")

#         # --- Basic validation ---
#         auth_user_id = data.get("auth_user_id")
#         if not auth_user_id:
#             logger.warning("⚠️ Missing auth_user_id in event. Skipping.")
#             continue

#         # --- Handle each event type ---
#         if event_type in ["USER_CREATED", "ADMIN_CREATED", "SUPERADMIN_CREATED"]:
#             with transaction.atomic():
#                 user, created = VerifiedUser.objects.update_or_create(
#                     auth_user_id=auth_user_id,
#                     defaults={
#                         "full_name": data.get("full_name"),
#                         "email": data.get("email"),
#                         "phone_number": data.get("phone_number"),
#                         "role": role or data.get("role", "admin"),
#                         "permissions": data.get("permissions", []),
#                     },
#                 )
#                 logger.info(f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser ({user.email})")

#         elif event_type == "USER_UPDATED":
#             updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
#                 full_name=data.get("full_name"),
#                 email=data.get("email"),
#                 phone_number=data.get("phone_number"),
#                 role=role or data.get("role"),
#             )
#             if updated:
#                 logger.info(f"🆙 VerifiedUser updated successfully: {data.get('email')}")
#             else:
#                 logger.warning(f"⚠️ No VerifiedUser found for update: {auth_user_id}")

#         elif event_type in ["USER_DELETED", "ADMIN_DELETED", "SUPERADMIN_DELETED"]:
#             deleted_count, _ = VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()
#             if deleted_count > 0:
#                 logger.info(f"🗑️ VerifiedUser deleted successfully: ID={auth_user_id}")
#             else:
#                 logger.warning(f"⚠️ No VerifiedUser found for deletion: ID={auth_user_id}")

#         else:
#             logger.warning(f"⚠️ Unknown event_type '{event_type}' received.")
#             logger.debug(f"Event details: {event}")

#     except Exception as e:
#         logger.exception(f"❌ Error while processing event '{event.get('event_type', 'UNKNOWN')}': {e}")
import os
import json
import django
import logging
from kafka import KafkaConsumer
from django.db import transaction
from django.conf import settings

# -----------------------------
# Django Setup
# -----------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser

# -----------------------------
# Logging
# -----------------------------# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger("kafka").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

logger.info("🚀 Starting SuperAdmin Kafka Consumer")
logger.info(f"📁 DB: {settings.DATABASES['default']['NAME']}")

# -----------------------------
# Role Normalizer
# -----------------------------
def normalize_role(role):
    if not role:
        return None
    return str(role).replace(" ", "").replace("_", "").lower()

# -----------------------------
# Kafka Consumer Setup
# -----------------------------
import time

consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            "service_provider_events",
            "admin_events",
            bootstrap_servers="localhost:9093",
            group_id="superadmin-service-group",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        logger.info("✅ Kafka Connected")
        logger.info("📡 Listening: admin_events, service_events")
    except Exception as e:
        logger.warning(f"⚠️ Kafka unavailable: {e}")
        logger.info("🔁 Retrying in 5 seconds...")
        time.sleep(5)

# -----------------------------
# Main Loop (Self-recovering)
# -----------------------------
while True:
    try:
        for message in consumer:
            logger.info(f"RAW MESSAGE: {message.value}")
            event = message.value
            event_type = event.get("event_type", "").upper()
            data = event.get("data", {})
            raw_role = event.get("role")
            role = normalize_role(raw_role)

            logger.info(f"📨 EVENT: {event_type} | Role={role} | Data={data}")

            # Validate
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id:
                logger.warning("⚠️ Missing auth_user_id, skipping.")
                continue

            # -----------------------------
            # FILTER: Only Admin/SuperAdmin (EXCEPT DELETION)
            # -----------------------------
            if role in ["individual", "organization", "employee"] and event_type != "USER_DELETED":
                logger.info(f"⏭️ Skipping {role} event (handled by Service Provider Service)")
                continue

            # -----------------------------
            # CREATE OR UPDATE USER
            # -----------------------------
            if event_type in ["USER_CREATED", "ADMIN_CREATED", "SUPERADMIN_CREATED"]:
                with transaction.atomic():
                    user, created = VerifiedUser.objects.update_or_create(
                        auth_user_id=auth_user_id,
                        defaults={
                            "full_name": data.get("full_name"),
                            "email": data.get("email"),
                            "phone_number": data.get("phone_number"),
                            "role": role,
                            "permissions": data.get("permissions", []),
                        },
                    )

                    if created:
                        logger.info(f"✅ Created VerifiedUser: {user.email}")
                    else:
                        logger.info(f"🔄 Updated VerifiedUser: {user.email}")

            # -----------------------------
            # USER UPDATED
            # -----------------------------
            elif event_type == "USER_UPDATED":
                updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
                    full_name=data.get("full_name"),
                    email=data.get("email"),
                    phone_number=data.get("phone_number"),
                    role=role,
                )

                if updated:
                    logger.info(f"🆙 Updated VerifiedUser: {data.get('email')}")
                else:
                    logger.warning(f"⚠️ User not found: {auth_user_id}")

            # -----------------------------
            # USER DELETED
            # -----------------------------
            elif event_type in ["USER_DELETED", "ADMIN_DELETED", "SUPERADMIN_DELETED"]:
                deleted, _ = VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()

                if deleted:
                    logger.info(f"🗑️ Deleted VerifiedUser ID={auth_user_id}")
                else:
                    logger.warning(f"⚠️ User not found for deletion: {auth_user_id}")

            elif event_type == "PROVIDER.DOCUMENT.UPLOADED":
                from dynamic_fields.models import ProviderDocumentVerification
                
                ProviderDocumentVerification.objects.create(
                    auth_user_id=data.get("auth_user_id"),
                    document_id=data.get("document_id"),
                    file_url=data.get("file_url"),
                    filename=data.get("filename"),
                    status="pending"
                )
                logger.info(f"✅ Document Verification Created: {data.get('filename')}")

            else:
                logger.warning(f"⚠️ Unknown event type: {event_type}")

    except Exception as e:
        logger.exception(f"❌ Consumer crashed: {e}")
        logger.info("🔁 Restarting in 3 seconds...")
        import time
        time.sleep(3)
