
import os
import json
import django
import logging
import time
from kafka import KafkaConsumer
import sys

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "veterinary_service.settings")
django.setup()

from veterinary.models import PetOwner

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("veterinary_consumer")

logger.info("🚀 Starting Veterinary Service Kafka Consumer...")

# Kafka init
from django.conf import settings

# Kafka init
consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            "auth_events", "service_provider_events",
            bootstrap_servers=settings.KAFKA_BROKER_URL,
            group_id="veterinary-service-group",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        logger.info("✅ Connected to Kafka broker.")
    except Exception as e:
        logger.warning(f"⚠️ Kafka unavailable: {e}")
        time.sleep(5)

for message in consumer:
    try:
        event = message.value
        event_type = (event.get("event_type") or "").upper()
        data = event.get("data") or {}

        if event_type == "USER_UPDATED":
            auth_user_id = data.get("id")
            if auth_user_id:
                owners = PetOwner.objects.filter(auth_user_id=auth_user_id)
                for owner in owners:
                    owner.first_name = data.get("first_name", owner.first_name)
                    owner.last_name = data.get("last_name", owner.last_name)
                    owner.email = data.get("email", owner.email)
                    owner.phone = data.get("phone", owner.phone)
                    owner.save()
                    owner.save()
                    logger.info(f"✅ Updated PetOwner {owner.id} from Auth User {auth_user_id}")

        elif event_type == "PROVIDER_CAPABILITY_UPDATED":
            provider_id = data.get("provider_id")
            capabilities = data.get("capabilities", {})
            if provider_id:
                try:
                    clinic = Clinic.objects.get(provider_id=provider_id)
                    clinic.capabilities = capabilities
                    clinic.save()
                    logger.info(f"✅ Updated Capabilities for Clinic {clinic.id} (Provider {provider_id})")
                except Clinic.DoesNotExist:
                    logger.warning(f"⚠️ Clinic not found for Provider {provider_id} - Skipping capability update")

    except Exception as e:
        logger.exception(f"❌ Error processing Kafka message: {e}")
