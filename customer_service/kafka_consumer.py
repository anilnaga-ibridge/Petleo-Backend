import os
import json
import django
import logging
import time
from kafka import KafkaConsumer
from django.db import transaction

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "customer_service.settings")
django.setup()

from customers.models import PetOwnerProfile

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("kafka").setLevel(logging.CRITICAL)
logger = logging.getLogger("customer_consumer")

# Create a debug file handler too
fh = logging.FileHandler("debug_consumer.txt")
fh.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info("🚀 Starting Customer Service Kafka Consumer...")

# Kafka init
consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            "individual_events",
            "organization_events",
            "pet_owner_events",
            bootstrap_servers="localhost:9093",
            group_id="customer-service-group",
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
        role = (event.get("role") or data.get("role") or "").lower()
        
        # We only care about Pet Owners / Customers
        if role not in ["petowner", "pet_owner", "pet owner", "customer"]:
            continue

        auth_user_id = data.get("auth_user_id")
        if not auth_user_id:
            continue

        logger.info(f"🔥 Event: {event_type} | User: {auth_user_id} | Role: {role}")

        if event_type in ["USER_CREATED", "USER_VERIFIED", "USER_UPDATED"]:
            with transaction.atomic():
                profile, created = PetOwnerProfile.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "full_name": data.get("full_name"),
                        "email": data.get("email"),
                        "phone_number": data.get("phone_number"),
                        "avatar_url": data.get("avatar_url"),
                    },
                )
                logger.info(
                    f"{'✅ Created' if created else '🔄 Updated'} PetOwnerProfile for {auth_user_id}"
                )

        elif event_type == "USER_DELETED":
            PetOwnerProfile.objects.filter(auth_user_id=auth_user_id).delete()
            logger.info(f"🗑️ Deleted PetOwnerProfile for {auth_user_id}")

    except Exception as e:
        logger.error(f"❌ Error processing Kafka message: {e}")
