


# import json
# import logging
# import time
# from kafka import KafkaProducer
# from kafka.errors import KafkaError, NoBrokersAvailable
# from django.conf import settings
# from django.apps import apps

# logger = logging.getLogger(__name__)

# # ==============================
# # Kafka Config
# # ==============================
# KAFKA_BROKER_URL = "localhost:9092"

# TOPIC_MAP = {
#     "individual": "individual_events",
#     "organization": "organization_events",
#     "admin": "admin_events",
#     "super_admin": "admin_events",
#     "pet_owner": "pet_owner_events",
# }

# SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# # ==============================
# # Producer Init
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
#         logger.info("✅ Connected to Kafka broker.")
#         break
#     except NoBrokersAvailable:
#         logger.warning(f"⚠️ Attempt {attempt+1}/5: Kafka not available. Retrying...")
#         time.sleep(5)
#     except Exception as e:
#         logger.error(f"❌ Kafka error: {e}")
#         break

# # ==============================
# # Convert role ID → role name
# # ==============================
# def get_role_name(role_value):
#     if role_value is None:
#         return None

#     # Already a name
#     if isinstance(role_value, str) and not role_value.isdigit():
#         return role_value.lower()

#     try:
#         role_id = int(role_value)
#         Role = apps.get_model("users", "Role")
#         role_obj = Role.objects.filter(id=role_id).first()
#         if role_obj:
#             return role_obj.name.lower()

#         logger.warning(f"⚠️ No role found with ID {role_value}")
#         return None
#     except Exception as e:
#         logger.error(f"⚠️ Role conversion error: {e}")
#         return None

# # ==============================
# # Publish Event
# # ==============================
# def publish_event(event_type, data: dict):
#     try:
#         raw_role = data.get("role")
#         role_name = get_role_name(raw_role)

#         if not role_name:
#             logger.warning(f"⚠️ Invalid role '{raw_role}'. Event not published.")
#             return

#         topic = TOPIC_MAP.get(role_name)
#         if not topic:
#             logger.warning(f"⚠️ No Kafka topic for role '{role_name}'")
#             return

#         event = {
#             "service": SERVICE_NAME,
#             "event_type": event_type.upper(),
#             "role": role_name,
#             "data": data,
#             "timestamp": int(time.time()),
#         }

#         logger.info(f"📦 Sending event '{event_type}' to '{topic}' (role={role_name})")
#         producer.send(topic, value=event)
#         producer.flush()
#         logger.info("✅ Event sent.")

#     except Exception as e:
#         logger.exception(f"❌ publish_event error: {e}")



import json
import logging
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from django.apps import apps
from django.conf import settings

logger = logging.getLogger(__name__)

KAFKA_BROKER_URL = getattr(settings, "KAFKA_BROKER", "localhost:9093")

TOPIC_MAP = {
    "individual": "individual_events",
    "organization": "organization_events",
    "admin": "admin_events",
    "super_admin": "admin_events",
    "superadmin": "admin_events",
    "serviceprovider": "service_provider_events",
    "petowner": "pet_owner_events",
    "pet_owner": "pet_owner_events",
    "employee": "service_provider_events",
    "receptionist": "service_provider_events",
    "veterinarian": "service_provider_events",
    "groomer": "service_provider_events",
    "doctor": "service_provider_events",
    "vitalsstaff": "service_provider_events",
    "vitals staff": "service_provider_events",
    "labtech": "service_provider_events",
    "lab tech": "service_provider_events",
}

SERVICE_NAME = getattr(settings, "SERVICE_NAME", "auth_service")

# ==============================
# Producer Init (Lazy)
# ==============================
_producer = None

def get_producer():
    global _producer
    if _producer:
        return _producer

    try:
        _producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER_URL],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=5,
        )
        logger.info("✅ Connected to Kafka broker.")
        return _producer
    except NoBrokersAvailable:
        logger.warning("⚠️ Kafka unavailable. Will retry on next event publish.")
        return None
    except Exception as e:
        logger.error(f"❌ Kafka error: {e}")
        return None

# ==============================
# Convert ANY role → canonical name
# ==============================
def get_role_name(role_value):
    """
    Acceptable inputs:
    - 1 / "1" (role ID)
    - "organization"
    - "Organization"
    - "ORGANIZATION"
    - Role object
    """

    if role_value is None:
        return None

    # Role object
    RoleModel = apps.get_model("users", "Role")
    if hasattr(role_value, "name"):
        return role_value.name.lower()

    # Strings (role names)
    if isinstance(role_value, str) and not role_value.isdigit():
        return role_value.strip().lower()

    # Numeric ID
    try:
        role_id = int(role_value)
        role_obj = RoleModel.objects.filter(id=role_id).first()
        if role_obj:
            return role_obj.name.lower()
        logger.warning(f"⚠️ Role ID '{role_value}' not found")
        return None
    except:
        logger.warning(f"⚠️ Invalid role format '{role_value}'")
        return None

# ==============================
# ==============================
# Publish Event
# ==============================
def publish_event(event_type, data: dict, **kwargs):
    """
    Publish an event to Kafka.
    Supports legacy calls with (event_type, data, role="name").
    """
    producer = get_producer()
    if not producer:
        logger.warning(f"⚠️ Kafka producer not available. Event '{event_type}' skipped.")
        return

    try:
        # Extract role either from data or from kwargs
        raw_role = data.get("role") or kwargs.get("role")
        role_name = get_role_name(raw_role)

        if not role_name:
            logger.warning(f"⚠️ Event '{event_type}' not sent — invalid role '{raw_role}'")
            return

        role_key = role_name.replace(" ", "").replace("_", "")

        topic = TOPIC_MAP.get(role_key)
        if not topic:
            logger.warning(f"⚠️ No Kafka topic mapped for role '{role_name}' [key={role_key}]")
            return

        event = {
            "service": SERVICE_NAME,
            "event_type": event_type.upper(),
            "role": role_name,
            "data": data,
            "timestamp": int(time.time()),
        }

        # Ensure role is in data for consumers that expect it there
        if "role" not in event["data"]:
            event["data"]["role"] = role_name

        logger.info(f"📦 Publishing event '{event_type}' → '{topic}' [role={role_name}]")
        producer.send(topic, value=event)
        # producer.flush()  # 🔥 Optimization: Removed blocking flush for better performance
        logger.info(f"✅ Kafka event '{event_type}' sent successfully")

    except Exception as e:
        logger.exception(f"❌ Failed to publish event '{event_type}': {e}")
