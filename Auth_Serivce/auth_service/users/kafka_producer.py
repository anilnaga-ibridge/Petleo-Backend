
# import json
# import logging
# import time
# from kafka import KafkaProducer
# from kafka.errors import KafkaError, NoBrokersAvailable
# from django.conf import settings

# logger = logging.getLogger(__name__)

# # -----------------------------
# # Kafka Configuration
# # -----------------------------
# # KAFKA_BROKER_URL = getattr(settings, "KAFKA_BROKER_URL", "localhost:9092")

# KAFKA_BROKER_URL = "host.docker.internal:9092"

# # Default topic (fallback)
# DEFAULT_TOPIC = getattr(settings, "KAFKA_EVENT_TOPIC", "service_events")

# # Role-based topic map
# TOPIC_MAP = {
#     "individual": "individual_events",
#     "organization": "organization_events",
#     "super_admin": "admin_events",
#     "pet_owner": "pet_owner_events",
# }

# SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# logger.info(f"🚀 Initializing Kafka Producer for service: {SERVICE_NAME}")
# logger.info(f"🔗 Connecting to Kafka broker at: {KAFKA_BROKER_URL}")

# # -----------------------------
# # Initialize Kafka Producer
# # -----------------------------
# producer = None
# for attempt in range(10):
#     try:
#         producer = KafkaProducer(
#             bootstrap_servers=[KAFKA_BROKER_URL],
#             value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#             acks="all",
#             retries=5,
#         )
#         logger.info("✅ Connected to Kafka broker successfully!")
#         break
#     except NoBrokersAvailable:
#         logger.warning(
#             f"⚠️ Attempt {attempt + 1}/10 — Kafka broker not available at {KAFKA_BROKER_URL}. Retrying in 5s..."
#         )
#         time.sleep(5)
#     except Exception as e:
#         logger.error(f"❌ Unexpected error while initializing Kafka Producer: {e}")
#         break

# if not producer:
#     logger.error("❌ Failed to connect to Kafka after 3 attempts — proceeding without Kafka connection.")
# def publish_user_created_event(user_data):
#     """
#     Publish user data to Kafka topic 'user_created'
#     Currently disabled - enable when Kafka is set up
#     """
#     # When Kafka is available, uncomment:
#     # producer.send('user_created', user_data)
#     # producer.flush()
    
#     # For now, just log the event
#     print(f"User created event: {user_data}")
#     pass
# # -----------------------------
# # Publish Event Function
# # -----------------------------
# def publish_event(event_type: str, data: dict, role: str = None):
#     """
#     Publishes an event to Kafka based on user role.
#     - 'individual' → service_provider_service
#     - 'organization' → service_provider_service
#     - 'super_admin' → super_admin_service
#     - 'pet_owner' → pet_owner_service
#     """

#     if not event_type or not isinstance(data, dict):
#         logger.warning("⚠️ Invalid Kafka event: missing event_type or data.")
#         return

#     if not producer:
#         logger.warning("⚠️ Kafka Producer not initialized. Skipping event publish.")
#         return

#     # Determine correct topic based on role
#     target_topic = TOPIC_MAP.get(role, DEFAULT_TOPIC)

#     event = {
#         "service": SERVICE_NAME,
#         "event_type": event_type,
#         "data": data,
#         "role": role,
#         "timestamp": int(time.time()),
#     }

#     try:
#         logger.info(
#             f"📤 Sending '{event_type}' for role='{role}' from {SERVICE_NAME} → topic '{target_topic}'..."
#         )
#         future = producer.send(target_topic, value=event)
#         future.get(timeout=10)
#         logger.info(
#             f"✅ Event '{event_type}' successfully sent to Kafka topic '{target_topic}'."
#         )
#     except KafkaError as e:
#         logger.error(f"❌ Kafka error while sending {event_type}: {e}")
#     except Exception as e:
#         logger.exception(f"⚠️ Unexpected error while sending {event_type}: {e}")

# import json
# import logging
# import time
# from kafka import KafkaProducer
# from kafka.errors import KafkaError, NoBrokersAvailable
# from django.conf import settings

# logger = logging.getLogger(__name__)

# # -----------------------------
# # Kafka Configuration
# # -----------------------------
# KAFKA_BROKER_URL = "host.docker.internal:9092"

# DEFAULT_TOPIC = getattr(settings, "KAFKA_EVENT_TOPIC", "service_events")

# # Role-based topic map
# TOPIC_MAP = {
#     "individual": "individual_events",
#     "organization": "organization_events",
#     "admin": "admin_events", # if the role admin sent then map to admin_events topic and send the super_admin_service
#     "pet_owner": "pet_owner_events",
# }

# SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# logger.info(f"🚀 Initializing Kafka Producer for service: {SERVICE_NAME}")
# logger.info(f"🔗 Connecting to Kafka broker at: {KAFKA_BROKER_URL}")

# # -----------------------------
# # Initialize Kafka Producer
# # -----------------------------
# producer = None
# for attempt in range(10):
#     try:
#         producer = KafkaProducer(
#             bootstrap_servers=[KAFKA_BROKER_URL],
#             value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#             acks="all",
#             retries=5,
#         )
#         logger.info("✅ Connected to Kafka broker successfully!")
#         break
#     except NoBrokersAvailable:
#         logger.warning(
#             f"⚠️ Attempt {attempt + 1}/10 — Kafka broker not available at {KAFKA_BROKER_URL}. Retrying in 5s..."
#         )
#         time.sleep(5)
#     except Exception as e:
#         logger.error(f"❌ Unexpected error while initializing Kafka Producer: {e}")
#         break

# if not producer:
#     logger.error("❌ Failed to connect to Kafka after 10 attempts — proceeding without Kafka connection.")

# # -----------------------------
# # Core Event Publisher
# # -----------------------------
# def publish_event(event_type: str, data: dict):
#     """
#     Publishes a structured event to Kafka.
#     Dynamically detects role and selects topic accordingly.
#     """
#     if not event_type or not isinstance(data, dict):
#         logger.warning("⚠️ Invalid Kafka event: missing event_type or data.")
#         return

#     if not producer:
#         logger.warning("⚠️ Kafka Producer not initialized. Skipping event publish.")
#         return

#     # Dynamically detect role from data
#     role = data.get("role")
#     target_topic = TOPIC_MAP.get(role, DEFAULT_TOPIC)

#     event = {
#         "service": SERVICE_NAME,
#         "event_type": event_type,
#         "data": data,
#         "role": role,
#         "timestamp": int(time.time()),
#     }

#     try:
#         logger.info(
#             f"📤 Sending '{event_type}' (role='{role}') from {SERVICE_NAME} → topic '{target_topic}'..."
#         )
#         future = producer.send(target_topic, value=event)
#         future.get(timeout=10)
#         logger.info(
#             f"✅ Event '{event_type}' successfully sent to Kafka topic '{target_topic}'."
#         )
#     except KafkaError as e:
#         logger.error(f"❌ Kafka error while sending {event_type}: {e}")
#     except Exception as e:
#         logger.exception(f"⚠️ Unexpected error while sending {event_type}: {e}")

# # -----------------------------
# # Specialized Event Publishers
# # -----------------------------
# def publish_user_created_event(user_data):
#     """Publish USER_CREATED event dynamically."""
#     event_data = {
#         "auth_user_id": str(user_data.get("id")),
#         "full_name": user_data.get("full_name"),
#         "email": user_data.get("email"),
#         "phone_number": user_data.get("phone_number"),
#         "role": user_data.get("role"),  # dynamic
#     }
#     publish_event("USER_CREATED", event_data)


# def publish_user_updated_event(user_data):
#     """Publish USER_UPDATED event dynamically."""
#     event_data = {
#         "auth_user_id": str(user_data.get("id")),
#         "full_name": user_data.get("full_name"),
#         "email": user_data.get("email"),
#         "phone_number": user_data.get("phone_number"),
#         "role": user_data.get("role"),  # dynamic
#     }
#     publish_event("USER_UPDATED", event_data)


# def publish_user_deleted_event(user_data):
#     """Publish USER_DELETED event dynamically."""
#     event_data = {
#         "auth_user_id": str(user_data.get("id")),
#         "role": user_data.get("role"),  # dynamic
#     }
#     publish_event("USER_DELETED", event_data)
# import json
# import logging
# import time
# from kafka import KafkaProducer
# from kafka.errors import KafkaError, NoBrokersAvailable
# from django.conf import settings

# logger = logging.getLogger(__name__)

# # -----------------------------
# # Kafka Configuration
# # -----------------------------
# KAFKA_BROKER_URL = "host.docker.internal:9092"

# # 🔹 Remove fallback usage; we will NOT use DEFAULT_TOPIC for safety
# DEFAULT_TOPIC = getattr(settings, "KAFKA_EVENT_TOPIC", None)

# # 🔹 Role → Kafka Topic Mapping
# TOPIC_MAP = {
#     "individual": "individual_events",
#     "organization": "organization_events",
#     "admin": "admin_events",       # ✅ admin users go to super_admin_service
#     "super_admin": "admin_events", # ✅ alias for consistency
#     "pet_owner": "pet_owner_events",
# }

# SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# logger.info(f"🚀 Initializing Kafka Producer for service: {SERVICE_NAME}")
# logger.info(f"🔗 Connecting to Kafka broker at: {KAFKA_BROKER_URL}")

# # -----------------------------
# # Initialize Kafka Producer
# # -----------------------------
# producer = None
# for attempt in range(10):
#     try:
#         producer = KafkaProducer(
#             bootstrap_servers=[KAFKA_BROKER_URL],
#             value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#             acks="all",
#             retries=5,
#         )
#         logger.info("✅ Connected to Kafka broker successfully!")
#         break
#     except NoBrokersAvailable:
#         logger.warning(
#             f"⚠️ Attempt {attempt + 1}/10 — Kafka broker not available at {KAFKA_BROKER_URL}. Retrying in 5s..."
#         )
#         time.sleep(5)
#     except Exception as e:
#         logger.error(f"❌ Unexpected error while initializing Kafka Producer: {e}")
#         break

# if not producer:
#     logger.error("❌ Failed to connect to Kafka after 10 attempts — proceeding without Kafka connection.")

# # -----------------------------
# # Core Event Publisher
# # -----------------------------
# def publish_event(event_type: str, data: dict):
#     """
#     Publishes a structured event to Kafka.
#     Dynamically detects role and selects topic accordingly.
#     """
#     if not event_type or not isinstance(data, dict):
#         logger.warning("⚠️ Invalid Kafka event: missing event_type or data.")
#         return

#     if not producer:
#         logger.warning("⚠️ Kafka Producer not initialized. Skipping event publish.")
#         return

#     # 🔹 Ensure role is present and valid
#     role = data.get("role")

#     if not role:
#         logger.warning(f"⚠️ Missing 'role' in data. Event '{event_type}' not published.")
#         return

#     if role not in TOPIC_MAP:
#         logger.warning(f"⚠️ Unknown role '{role}'. Event '{event_type}' not published.")
#         return

#     target_topic = TOPIC_MAP[role]

#     event = {
#         "service": SERVICE_NAME,
#         "event_type": event_type,
#         "data": data,
#         "role": role,
#         "timestamp": int(time.time()),
#     }

#     try:
#         logger.info(
#             f"📦 Routing event '{event_type}' for role='{role}' → topic='{target_topic}'"
#         )
#         future = producer.send(target_topic, value=event)
#         future.get(timeout=10)
#         logger.info(f"✅ Event '{event_type}' sent successfully to topic '{target_topic}'")
#     except KafkaError as e:
#         logger.error(f"❌ Kafka error while sending {event_type}: {e}")
#     except Exception as e:
#         logger.exception(f"⚠️ Unexpected error while sending {event_type}: {e}")

# # -----------------------------
# # Specialized Event Publishers
# # -----------------------------
# def publish_user_created_event(user_data):
#     """Publish USER_CREATED event dynamically."""
#     event_data = {
#         "auth_user_id": str(user_data.get("id")),
#         "full_name": user_data.get("full_name"),
#         "email": user_data.get("email"),
#         "phone_number": user_data.get("phone_number"),
#         "role": user_data.get("role"),
#     }
#     publish_event("USER_CREATED", event_data)


# def publish_user_updated_event(user_data):
#     """Publish USER_UPDATED event dynamically."""
#     event_data = {
#         "auth_user_id": str(user_data.get("id")),
#         "full_name": user_data.get("full_name"),
#         "email": user_data.get("email"),
#         "phone_number": user_data.get("phone_number"),
#         "role": user_data.get("role"),
#     }
#     publish_event("USER_UPDATED", event_data)


# def publish_user_deleted_event(user_data):
#     """Publish USER_DELETED event dynamically."""
#     event_data = {
#         "auth_user_id": str(user_data.get("id")),
#         "role": user_data.get("role"),
#     }
#     publish_event("USER_DELETED", event_data)




# import json
# import logging
# import time
# from kafka import KafkaProducer
# from kafka.errors import KafkaError, NoBrokersAvailable
# from django.conf import settings

# logger = logging.getLogger(__name__)

# # ==============================
# # Kafka Configuration
# # ==============================
# KAFKA_BROKER_URL = "host.docker.internal:9092"

# TOPIC_MAP = {
#     "individual": "individual_events",
#     "organization": "organization_events",
#     "admin": "admin_events",
#     "super_admin": "admin_events",
#     "pet_owner": "pet_owner_events",
# }

# SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# # ==============================
# # Kafka Producer Initialization
# # ==============================
# producer = None
# for attempt in range(5):
#     try:
#         producer = KafkaProducer(
#             bootstrap_servers=[KAFKA_BROKER_URL],
#             value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#             acks="all",
#             retries=5,
#         )
#         logger.info("✅ Connected to Kafka broker successfully!")
#         break
#     except NoBrokersAvailable:
#         logger.warning(
#             f"⚠️ Attempt {attempt + 1}/5 — Kafka broker not available at {KAFKA_BROKER_URL}. Retrying in 5s..."
#         )
#         time.sleep(5)
#     except Exception as e:
#         logger.error(f"❌ Error initializing Kafka Producer: {e}")
#         break

# if not producer:
#     logger.error("❌ Kafka Producer failed to connect after multiple retries.")

# # ==============================
# # Core Event Publisher
# # ==============================
# def publish_event(event_type: str, data: dict):
#     """
#     Publish a structured event to the correct Kafka topic based on user role.
#     """
#     try:
#         if not event_type or not isinstance(data, dict):
#             logger.warning("⚠️ Invalid event_type or data in publish_event.")
#             return

#         role = (data.get("role") or "").lower()
#         if not role:
#             logger.warning(f"⚠️ Missing 'role' in data. Event '{event_type}' not published.")
#             return

#         topic = TOPIC_MAP.get(role)
#         if not topic:
#             logger.warning(f"⚠️ Unknown role '{role}'. Event '{event_type}' not published.")
#             return

#         event = {
#             "service": SERVICE_NAME,
#             "event_type": event_type.upper(),
#             "data": data,
#             "role": role,
#             "timestamp": int(time.time()),
#         }

#         logger.info(f"📦 Sending event '{event_type}' → topic '{topic}' with data={data}")
#         future = producer.send(topic, value=event)
#         future.get(timeout=10)
#         logger.info(f"✅ Event '{event_type}' successfully sent to '{topic}'")

#     except KafkaError as e:
#         logger.error(f"❌ Kafka error while sending event: {e}")
#     except Exception as e:
#         logger.exception(f"⚠️ Unexpected error while sending event: {e}")
import json
import logging
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from django.conf import settings
from django.apps import apps  # ✅ To dynamically load models

logger = logging.getLogger(__name__)

# ==============================
# Kafka Configuration
# ==============================
KAFKA_BROKER_URL = "host.docker.internal:9092"

TOPIC_MAP = {
    "individual": "individual_events",
    "organization": "organization_events",
    "admin": "admin_events",
    "super_admin": "admin_events",
    "pet_owner": "pet_owner_events",
}

SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# ==============================
# Kafka Producer Initialization
# ==============================
producer = None
for attempt in range(5):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER_URL],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=5,
        )
        logger.info("✅ Connected to Kafka broker successfully!")
        break
    except NoBrokersAvailable:
        logger.warning(
            f"⚠️ Attempt {attempt + 1}/5 — Kafka broker not available at {KAFKA_BROKER_URL}. Retrying in 5s..."
        )
        time.sleep(5)
    except Exception as e:
        logger.error(f"❌ Error initializing Kafka Producer: {e}")
        break

if not producer:
    logger.error("❌ Kafka Producer failed to connect after multiple retries.")


# ==============================
# Utility: Get Role Name by ID
# ==============================
def get_role_name(role_value):
    """
    Accepts either role name (string) or role ID (int/UUID) and returns the role name.
    """
    if not role_value:
        return None

    # If already a string, assume it's the role name
    if isinstance(role_value, str) and not role_value.isdigit():
        return role_value.lower()

    try:
        Role = apps.get_model("users", "Role")  # ✅ app_label, model_name
        role_obj = Role.objects.filter(id=role_value).first()
        if role_obj:
            return role_obj.name.lower()
        logger.warning(f"⚠️ Role with ID '{role_value}' not found in DB.")
        return None
    except Exception as e:
        logger.error(f"⚠️ Error fetching role name for ID '{role_value}': {e}")
        return None


# ==============================
# Core Event Publisher
# ==============================
def publish_event(event_type: str, data: dict):
    """
    Publish a structured event to the correct Kafka topic based on user role.
    Handles both role IDs and role names automatically.
    """
    try:
        if not event_type or not isinstance(data, dict):
            logger.warning("⚠️ Invalid event_type or data in publish_event.")
            return

        # ✅ Resolve role name even if ID is provided
        raw_role = data.get("role")
        role_name = get_role_name(raw_role)

        if not role_name:
            logger.warning(f"⚠️ Invalid or missing role '{raw_role}'. Event '{event_type}' not published.")
            return

        topic = TOPIC_MAP.get(role_name)
        if not topic:
            logger.warning(f"⚠️ Unknown role '{role_name}'. Event '{event_type}' not published.")
            return

        event = {
            "service": SERVICE_NAME,
            "event_type": event_type.upper(),
            "data": data,
            "role": role_name,
            "timestamp": int(time.time()),
        }

        logger.info(f"📦 Sending event '{event_type}' → topic '{topic}' with role='{role_name}' and data={data}")
        future = producer.send(topic, value=event)
        future.get(timeout=10)
        logger.info(f"✅ Event '{event_type}' successfully sent to '{topic}'")

    except KafkaError as e:
        logger.error(f"❌ Kafka error while sending event: {e}")
    except Exception as e:
        logger.exception(f"⚠️ Unexpected error while sending event: {e}")
