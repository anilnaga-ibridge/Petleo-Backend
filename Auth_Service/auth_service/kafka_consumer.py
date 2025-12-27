import os
import json
import django
import logging
import time
from kafka import KafkaConsumer

import sys
import os

# Add parent directory to sys.path to allow importing auth_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auth_consumer")

logger.info("🚀 Starting Auth Service Kafka Consumer...")

# Kafka init
consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            "service_provider_events",
            bootstrap_servers="localhost:9093",
            group_id="auth-service-group",
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
        role = (event.get("role") or "").lower()

        if event_type == "EMPLOYEE_UPDATED":
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id: continue

            try:
                user = User.objects.get(id=auth_user_id)
                user.full_name = data.get("full_name", user.full_name)
                user.phone_number = data.get("phone_number", user.phone_number)
                # Email update might be tricky if it's the username, but let's try
                if data.get("email"):
                    user.email = data.get("email")
                user.save()
                logger.info(f"✅ Updated User {auth_user_id}")
            except User.DoesNotExist:
                logger.warning(f"⚠️ User {auth_user_id} not found for update")

        elif event_type == "EMPLOYEE_DELETED":
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id: continue

            try:
                user = User.objects.get(id=auth_user_id)
                user.is_active = False # Deactivate instead of delete to preserve history/integrity
                user.save()
                logger.info(f"🚫 Deactivated User {auth_user_id}")
            except User.DoesNotExist:
                logger.warning(f"⚠️ User {auth_user_id} not found for deletion")

        elif event_type == "SEND_EMAIL":
            user_id = data.get("user_id")
            if user_id:
                try:
                    from users.email_utils import send_automatic_registration_email_for_user
                    user = User.objects.get(id=user_id)
                    send_automatic_registration_email_for_user(user)
                    logger.info(f"✅ Sent registration email for User {user_id}")
                except User.DoesNotExist:
                    logger.warning(f"⚠️ User {user_id} not found for email sending")
                except Exception as e:
                    logger.error(f"❌ Failed to send email for User {user_id}: {e}")

    except Exception as e:
        logger.exception(f"❌ Error processing Kafka message: {e}")
