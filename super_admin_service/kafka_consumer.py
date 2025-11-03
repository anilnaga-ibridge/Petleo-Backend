
# # super_admin/kafka_consumer.py

# from kafka import KafkaConsumer
# import json
# import os
# import django
# from admin_core.models import VerifiedUser
# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()



# consumer = KafkaConsumer(
#     'user_created',
#     bootstrap_servers='localhost:9092',
#     auto_offset_reset='earliest',
#     group_id='superadmin_group',
#     value_deserializer=lambda m: json.loads(m.decode('utf-8'))
# )

# print("SuperAdmin Service Kafka consumer started...")

# for message in consumer:
#     data = message.value

#     auth_user_id = data.get("auth_user_id")
#     email = data.get("email")
#     full_name = data.get("full_name") or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
#     phone_number = data.get("phone_number") or data.get("contact")
#     role = data.get("role")
#     permissions = data.get("permissions", [])

#     if not auth_user_id or not email:
#         print("Skipping message: auth_user_id or email missing")
#         continue

#     # Avoid duplicates
#     if VerifiedUser.objects.filter(auth_user_id=auth_user_id).exists():
#         print(f"VerifiedUser already exists: {email}")
#         continue

#     verified_user_data = {
#         "auth_user_id": auth_user_id,
#         "full_name": full_name,
#         "email": email,
#         "phone_number": phone_number,
#         "role": role,
#         "permissions": permissions,
#     }

#     VerifiedUser.objects.create(**verified_user_data)
#     print(f"VerifiedUser created: {email}")
import os
import json
import django
import logging
from kafka import KafkaConsumer

# --- Django setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
django.setup()

from admin_core.models import VerifiedUser  # ✅ your model

# --- Logging setup ---
logger = logging.getLogger("super_admin_consumer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger.info("🚀 Starting SuperAdmin Kafka Consumer...")

# --- Kafka Consumer setup ---
consumer = KafkaConsumer(
    "service_events",                          # ✅ topic name
    bootstrap_servers="localhost:9092",
    group_id="superadmin-service-group",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

logger.info("✅ Connected to Kafka broker successfully.")
logger.info("📡 Listening to topic 'service_events'...")

# --- Event processing ---
for message in consumer:
    event = message.value
    logger.info(f"📨 Received event: {event}")

    event_type = event.get("event_type")
    data = event.get("data", {})

    try:
        if event_type == "USER_CREATED":
            logger.info("🧩 Processing USER_CREATED event...")

            user, created = VerifiedUser.objects.get_or_create(
                auth_user_id=data["auth_user_id"],
                defaults={
                    "full_name": data.get("full_name"),
                    "email": data.get("email"),
                    "phone_number": data.get("phone_number"),
                    "role": data.get("role"),
                    "permissions": data.get("permissions", []),
                },
            )

            if created:
                logger.info(f"✅ New VerifiedUser created: {user.email}")
            else:
                logger.info(f"ℹ️ VerifiedUser already exists: {user.email}")

        elif event_type == "USER_VERIFIED":
            logger.info("🔐 Processing USER_VERIFIED event...")

            updated = VerifiedUser.objects.filter(
                email=data.get("email")
            ).update(
                full_name=data.get("full_name"),
                role=data.get("role"),
                permissions=data.get("permissions", []),
            )

            if updated:
                logger.info(f"✅ VerifiedUser '{data['email']}' marked as verified.")
            else:
                logger.warning(f"⚠️ VerifiedUser not found for email: {data.get('email')}")

        else:
            logger.warning(f"⚠️ Unknown event type received: {event_type}")

    except Exception as e:
        logger.error(f"❌ Error while processing {event_type}: {e}", exc_info=True)

# Optional: uncomment this if running as a standalone script
# if __name__ == "__main__":
#     start_kafka_consumer()


# # superadmin_consumer.py
# from kafka import KafkaConsumer
# import json
# import os
# import django

# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import SuperAdmin

# consumer = KafkaConsumer(
#     'user_created',
#     bootstrap_servers='localhost:9092',
#     auto_offset_reset='earliest',
#     group_id='superadmin_group',
#     value_deserializer=lambda m: json.loads(m.decode('utf-8'))
# )

# print("SuperAdmin Service Kafka consumer started...")

# for message in consumer:
#     data = message.value

#     auth_user_id = data.get("auth_user_id")
#     email = data.get("email")

#     if not auth_user_id or not email:
#         print("Skipping message: auth_user_id or email missing")
#         continue

#     # Avoid duplicates
#     if SuperAdmin.objects.filter(auth_user_id=auth_user_id).exists():
#         print(f"SuperAdmin already exists: {email}")
#         continue

#     extra = data.get("extra_fields", {})

#     superadmin_data = {
#         "auth_user_id": auth_user_id,
#         "email": email,
#         "first_name": extra.get("first_name", ""),
#         "last_name": extra.get("last_name", ""),
#         "username": extra.get("username", ""),
#         "phone": extra.get("phone", ""),
#         "contact": extra.get("contact", ""),
#         "user_role": extra.get("user_role", data.get("role", "superAdmin")),
#         "is_active": extra.get("is_active", True),
#         "is_staff": extra.get("is_staff", True),
#         "is_superuser": extra.get("is_superuser", True),
#         "is_super_admin": extra.get("is_super_admin", True),
#         "activity_status": extra.get("activity_status", "active")
#     }

#     try:
#         SuperAdmin.objects.create(**superadmin_data)
#         print(f"SuperAdmin created: {email}")
#     except Exception as e:
#         print(f"Error creating SuperAdmin {email}: {e}")
# import os
# import django
# import json
# from kafka import KafkaConsumer
# from kafka.errors import KafkaError

# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import SuperAdmin

# # Initialize Kafka consumer
# consumer = KafkaConsumer(
#     'user_created',
#     bootstrap_servers='localhost:9092',
#     auto_offset_reset='earliest',
#     enable_auto_commit=True,
#     group_id='superadmin_group',
#     value_deserializer=lambda m: json.loads(m.decode('utf-8'))
# )

# print("🚀 SuperAdmin Service Kafka consumer started...")

# allowed_fields = [f.name for f in SuperAdmin._meta.get_fields()]

# for message in consumer:
#     try:
#         print("\n📩 Message received from Kafka:", message.value)
#         data = message.value

#         auth_user_id = data.get("auth_user_id")
#         email = data.get("email")

#         if not auth_user_id or not email:
#             print("⚠️ Skipping message: missing auth_user_id or email")
#             continue

#         # Check if already exists
#         if SuperAdmin.objects.filter(auth_user_id=auth_user_id).exists() or \
#            SuperAdmin.objects.filter(email=email).exists():
#             print(f"ℹ️ SuperAdmin already exists: {email}")
#             continue

#         extra = data.get("extra_fields", {})

#         # Prepare data
#         superadmin_data = {
#             "auth_user_id": auth_user_id,
#             "email": email,
#             "first_name": extra.get("first_name", ""),
#             "last_name": extra.get("last_name", ""),
#             "username": extra.get("username", ""),
#             "phone": extra.get("phone", ""),
#             "contact": extra.get("contact", ""),
#             "user_role": extra.get("user_role", data.get("role", "superAdmin")),
#             "is_active": True,
#             "is_staff": True,
#             "is_admin": True,
#             "is_super_admin": True,
#             "activity_status": "active"
#         }

#         # Keep only valid model fields
#         superadmin_data = {k: v for k, v in superadmin_data.items() if k in allowed_fields}

#         # Create record
#         SuperAdmin.objects.create(**superadmin_data)
#         print(f"✅ SuperAdmin created successfully: {email}")

#     except KafkaError as ke:
#         print(f"❌ Kafka error: {ke}")
#     except Exception as e:
#         print(f"🔥 Error creating SuperAdmin {email if 'email' in locals() else ''}: {e}")



# import os
# import django
# import json
# import logging
# from kafka import KafkaConsumer
# from kafka.errors import KafkaError

# # -----------------------------
# # Django setup
# # -----------------------------
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import SuperAdmin

# # -----------------------------
# # Logging setup
# # -----------------------------
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger(__name__)

# # -----------------------------
# # Kafka setup
# # -----------------------------
# KAFKA_BROKER_URL = "localhost:9092"
# KAFKA_TOPIC = "user_events"
# GROUP_ID = "superadmin_group"

# logger.info("🚀 Starting SuperAdmin Kafka consumer...")

# consumer = KafkaConsumer(
#     KAFKA_TOPIC,
#     bootstrap_servers=[KAFKA_BROKER_URL],
#     auto_offset_reset='earliest',
#     enable_auto_commit=True,
#     group_id=GROUP_ID,
#     value_deserializer=lambda m: json.loads(m.decode('utf-8')),
# )

# allowed_fields = [f.name for f in SuperAdmin._meta.get_fields()]

# # -----------------------------
# # Consumer Loop
# # -----------------------------
# for message in consumer:
#     try:
#         event_data = message.value
#         logger.info(f"\n📩 Received Kafka message: {event_data}")

#         data = event_data.get("data", {})  # Support both wrapper formats

#         # Extract fields
#         auth_user_id = event_data.get("auth_user_id") or data.get("id") or data.get("auth_user_id")
#         email = event_data.get("email") or data.get("email")
#         role = (event_data.get("role") or data.get("role") or "").lower()
#         contact = event_data.get("contact") or data.get("contact") or ""

#         if not auth_user_id or not email:
#             logger.warning("⚠️ Missing auth_user_id or email. Skipping message.")
#             continue

#         if role not in ["admin", "superadmin"]:
#             logger.info(f"ℹ️ Skipping non-superadmin/admin user: {email} ({role})")
#             continue

#         if SuperAdmin.objects.filter(auth_user_id=auth_user_id).exists():
#             logger.info(f"ℹ️ SuperAdmin already exists for user_id {auth_user_id}")
#             continue

#         if SuperAdmin.objects.filter(email=email).exists():
#             logger.info(f"ℹ️ SuperAdmin with email {email} already exists")
#             continue

#         superadmin_data = {
#             "auth_user_id": auth_user_id,
#             "email": email,
#             "contact": contact,
#             "user_role": "Admin",
#             "is_active": True,
#             "is_staff": True,
#             "is_admin": True,
#             "is_super_admin": True,
#             "activity_status": "active"
#         }

#         # Only include valid model fields
#         superadmin_data = {k: v for k, v in superadmin_data.items() if k in allowed_fields}

#         superadmin = SuperAdmin.objects.create(**superadmin_data)
#         logger.info(f"✅ SuperAdmin created successfully: {superadmin.email}")

#     except KafkaError as ke:
#         logger.error(f"❌ Kafka error: {ke}")
#     except Exception as e:
#         logger.exception(f"🔥 Error processing message: {e}")


# import os
# import django
# import json
# import uuid
# import logging
# from kafka import KafkaConsumer
# from kafka.errors import KafkaError
# from django.utils import timezone

# # -----------------------------
# # Django setup
# # -----------------------------
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import VerifiedUser, SuperAdmin

# # -----------------------------
# # Logging setup
# # -----------------------------
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger(__name__)

# # -----------------------------
# # Kafka setup
# # -----------------------------
# KAFKA_BROKER_URL = "localhost:9092"
# KAFKA_TOPIC = "user_events"
# GROUP_ID = "superadmin_group"

# logger.info("🚀 Starting VerifiedUser Kafka consumer...")

# consumer = KafkaConsumer(
#     KAFKA_TOPIC,
#     bootstrap_servers=[KAFKA_BROKER_URL],
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     group_id=GROUP_ID,
#     value_deserializer=lambda m: json.loads(m.decode("utf-8")),
# )

# # -----------------------------
# # Consumer Loop
# # -----------------------------
# for message in consumer:
#     try:
#         event = message.value
#         logger.info(f"\n📩 Received Kafka message: {event}")

#         event_type = event.get("event_type")
#         if event_type != "USER_VERIFIED":
#             logger.info(f"ℹ️ Ignoring unrelated event type: {event_type}")
#             continue

#         # Extract and validate data
#         data = event.get("data", {})
#         auth_user_id_str = data.get("auth_user_id")
#         if not auth_user_id_str:
#             logger.warning("⚠️ Missing auth_user_id — skipping message.")
#             continue

#         try:
#             auth_user_id = uuid.UUID(auth_user_id_str)
#         except ValueError:
#             logger.warning(f"⚠️ Invalid UUID: {auth_user_id_str}")
#             continue

#         full_name = data.get("full_name")
#         email = data.get("email")
#         phone_number = data.get("phone_number")
#         role = (data.get("role") or "").lower()
#         permissions = data.get("permissions", [])

#         # ✅ Create or Update VerifiedUser
#         verified_user, created = VerifiedUser.objects.update_or_create(
#             auth_user_id=auth_user_id,
#             defaults={
#                 "full_name": full_name,
#                 "email": email,
#                 "phone_number": phone_number,
#                 "role": role,
#                 "permissions": permissions,
#                 "updated_at": timezone.now(),
#             },
#         )

#         if created:
#             logger.info(f"✅ New VerifiedUser created: {verified_user.email}")
#         else:
#             logger.info(f"♻️ VerifiedUser updated: {verified_user.email}")

#         # ✅ Optional: Create SuperAdmin if role matches
#         if role in ["admin", "superadmin"]:
#             if not SuperAdmin.objects.filter(auth_user_id=str(auth_user_id)).exists():
#                 SuperAdmin.objects.create(
#                     auth_user_id=str(auth_user_id),
#                     email=email,
#                     contact=phone_number,
#                     first_name=(full_name or "").split(" ")[0],
#                     last_name=" ".join((full_name or "").split(" ")[1:]),
#                     user_role=role.capitalize(),
#                     is_active=True,
#                     is_staff=True,
#                     is_admin=True,
#                     is_super_admin=True,
#                     activity_status="active",
#                 )
#                 logger.info(f"✅ SuperAdmin created successfully: {email}")
#             else:
#                 logger.info(f"ℹ️ SuperAdmin already exists for {email}")

#     except KafkaError as ke:
#         logger.error(f"❌ Kafka error: {ke}")
#     except Exception as e:
#         logger.exception(f"🔥 Error processing message: {e}")



# import os
# import django
# import json
# import uuid
# import logging
# from kafka import KafkaConsumer
# from kafka.errors import KafkaError
# from django.utils import timezone

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_admin_service.settings")
# django.setup()

# from admin_core.models import VerifiedUser, SuperAdmin

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger(__name__)

# KAFKA_BROKER_URL = "localhost:9092"
# KAFKA_TOPIC = "user_events"
# GROUP_ID = "superadmin_group"

# logger.info("🚀 Starting VerifiedUser Kafka consumer...")

# consumer = KafkaConsumer(
#     KAFKA_TOPIC,
#     bootstrap_servers=[KAFKA_BROKER_URL],
#     auto_offset_reset="earliest",
#     enable_auto_commit=True,
#     group_id=GROUP_ID,
#     value_deserializer=lambda m: json.loads(m.decode("utf-8")),
# )

# for message in consumer:
#     try:
#         event = message.value
#         logger.info(f"\n📩 Received Kafka message: {event}")

#         event_type = event.get("event_type")
#         if event_type != "USER_VERIFIED":
#             logger.info(f"ℹ️ Ignoring unrelated event: {event_type}")
#             continue

#         data = event.get("data", {})
#         auth_user_id_str = data.get("auth_user_id")

#         if not auth_user_id_str:
#             logger.warning("⚠️ Missing auth_user_id — skipping.")
#             continue

#         try:
#             auth_user_id = uuid.UUID(auth_user_id_str)
#         except ValueError:
#             logger.warning(f"⚠️ Invalid UUID: {auth_user_id_str}")
#             continue

#         full_name = data.get("full_name")
#         email = data.get("email")
#         phone_number = data.get("phone_number")
#         role = (data.get("role") or "").lower()
#         permissions = data.get("permissions", [])

#         logger.info(f"🧩 Attempting to upsert VerifiedUser for {email}...")

#         # ✅ Create or Update VerifiedUser
#         verified_user, created = VerifiedUser.objects.update_or_create(
#             auth_user_id=auth_user_id,
#             defaults={
#                 "full_name": full_name,
#                 "email": email,
#                 "phone_number": phone_number,
#                 "role": role,
#                 "permissions": permissions,
#                 "updated_at": timezone.now(),
#             },
#         )

#         if created:
#             logger.info(f"✅ Created VerifiedUser: {verified_user.email}")
#         else:
#             logger.info(f"♻️ Updated VerifiedUser: {verified_user.email}")

#         # ✅ Only create SuperAdmin for admin roles
#         if role in ["admin", "superadmin"]:
#             if not SuperAdmin.objects.filter(auth_user_id=str(auth_user_id)).exists():
#                 SuperAdmin.objects.create(
#                     auth_user_id=str(auth_user_id),
#                     email=email,
#                     contact=phone_number,
#                     first_name=(full_name or "").split(" ")[0],
#                     last_name=" ".join((full_name or "").split(" ")[1:]),
#                     user_role=role.capitalize(),
#                     is_active=True,
#                     is_staff=True,
#                     is_admin=True,
#                     is_super_admin=True,
#                     activity_status="active",
#                 )
#                 logger.info(f"✅ SuperAdmin created for {email}")
#             else:
#                 logger.info(f"ℹ️ SuperAdmin already exists for {email}")

#     except Exception as e:
#         logger.exception(f"🔥 ERROR while processing Kafka message: {e}")
