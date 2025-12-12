import os
import json
import django
import logging
from kafka import KafkaConsumer
from django.db import transaction

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import LocalFieldDefinition, LocalDocumentDefinition

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("kafka").setLevel(logging.CRITICAL)
logger = logging.getLogger("service_provider_consumer")

logger.info("🚀 Starting Service Provider Unified Kafka Consumer...")

# Normalize role safely
def normalize_role(role):
    if not role:
        return None
    return str(role).replace(" ", "").replace("_", "").lower()

# Kafka setup
# Kafka setup
import time

consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            "individual_events",
            "organization_events",
            "admin_events",  # Added admin_events
            bootstrap_servers="localhost:9093",
            group_id="service-provider-group",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        logger.info("✅ Connected to Kafka broker.")
        logger.info("📡 Listening to: individual_events, organization_events, admin_events")
    except Exception as e:
        logger.warning(f"⚠️ Kafka unavailable: {e}")
        logger.info("🔁 Retrying in 5 seconds...")
        time.sleep(5)

for message in consumer:
    try:
        event = message.value
        event_type = (event.get("event_type") or "").upper()
        # Handle payload vs data structure difference
        data = event.get("data") or event.get("payload") or {}
        role = event.get("role")
        service = event.get("service")

        logger.info(f"🔥 Received event: {event_type} | Role: {role} | Service: {service}")

        # -----------------------------
        # FILTER: Ignore Admin/SuperAdmin User Events
        # -----------------------------
        if role in ["admin", "super_admin"] and event_type in ["USER_CREATED", "USER_UPDATED", "USER_DELETED", "USER_VERIFIED"]:
            logger.info(f"⏭️ Skipping {role} user event (handled by Super Admin Service)")
            continue

        # ==========================
        # AUTH & USER EVENTS
        # ==========================
        if event_type in ["USER_CREATED", "USER_VERIFIED"]:
            if not data.get("auth_user_id"):
                logger.warning("⚠️ Missing auth_user_id. Skipping message.")
                continue

            auth_user_id = data["auth_user_id"]
            with transaction.atomic():
                # Use auth_user_id as the Primary Key (id)
                user, created = VerifiedUser.objects.update_or_create(
                    id=auth_user_id, 
                    defaults={
                        "auth_user_id": auth_user_id,
                        "full_name": data.get("full_name"),
                        "email": data.get("email"),
                        "phone_number": data.get("phone_number"),
                        "role": role or data.get("role"),
                        "permissions": data.get("permissions", []),
                    },
                )
                logger.info(f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser ({user.email})")

        elif event_type == "USER_UPDATED":
            if not data.get("auth_user_id"):
                continue
            auth_user_id = data["auth_user_id"]
            updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
                full_name=data.get("full_name"),
                email=data.get("email"),
                phone_number=data.get("phone_number"),
                role=role or data.get("role"),
            )
            if updated:
                logger.info(f"🆙 VerifiedUser updated: {data.get('email')}")
            else:
                logger.warning(f"⚠️ No VerifiedUser found for update: {auth_user_id}")

        elif event_type == "USER_DELETED":
            if not data.get("auth_user_id"):
                continue
            auth_user_id = data["auth_user_id"]
            deleted, _ = VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()
            if deleted > 0:
                logger.info(f"🗑️ VerifiedUser deleted successfully: ID={auth_user_id}")
            else:
                logger.warning(f"⚠️ No VerifiedUser found for deletion: ID={auth_user_id}")

        # ==========================
        # DYNAMIC FIELDS SYNC
        # ==========================
        elif event_type in ["FIELD_DEFINITION_CREATED", "FIELD_DEFINITION_UPDATED"]:
            LocalFieldDefinition.objects.update_or_create(
                id=data["id"],
                defaults={
                    "target": data["target"],
                    "name": data["name"],
                    "label": data["label"],
                    "field_type": data["field_type"],
                    "is_required": data["is_required"],
                    "options": data.get("options", []),
                    "order": data.get("order", 0),
                    "help_text": data.get("help_text", ""),
                }
            )
            logger.info(f"✅ Synced Field Definition: {data.get('label')}")

        elif event_type == "FIELD_DEFINITION_DELETED":
            LocalFieldDefinition.objects.filter(id=data["id"]).delete()
            logger.info(f"🗑️ Deleted Field Definition: {data.get('id')}")

        # ==========================
        # DOCUMENT DEFINITIONS SYNC
        # ==========================
        elif event_type in ["DOCUMENT_DEFINITION_CREATED", "DOCUMENT_DEFINITION_UPDATED"]:
            LocalDocumentDefinition.objects.update_or_create(
                id=data["id"],
                defaults={
                    "target": data["target"],
                    "key": data["key"],
                    "label": data["label"],
                    "is_required": data["is_required"],
                    "allow_multiple": data["allow_multiple"],
                    "allowed_types": data.get("allowed_types", []),
                    "order": data.get("order", 0),
                    "help_text": data.get("help_text", ""),
                }
            )
            logger.info(f"✅ Synced Document Definition: {data.get('label')}")

        elif event_type == "DOCUMENT_DEFINITION_DELETED":
            LocalDocumentDefinition.objects.filter(id=data["id"]).delete()
            logger.info(f"🗑️ Deleted Document Definition: {data.get('id')}")

        # ==========================
        # PERMISSIONS SYNC
        # ==========================
        elif event_type == "provider.permissions.updated":
            auth_user_id = data.get("auth_user_id") or data.get("data", {}).get("auth_user_id")
            permissions = data.get("permissions") or data.get("data", {}).get("permissions", [])
            
            if auth_user_id:
                updated_count = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(permissions=permissions)
                if updated_count:
                    logger.info(f"✅ Updated permissions for user {auth_user_id}")
                else:
                    logger.warning(f"⚠️ User {auth_user_id} not found for permission update")

        elif event_type == "provider.permissions.revoked":
            auth_user_id = data.get("auth_user_id") or data.get("data", {}).get("auth_user_id")
            
            if auth_user_id:
                updated_count = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(permissions=[])
                if updated_count:
                    logger.info(f"🚫 Revoked permissions for user {auth_user_id}")
                else:
                    logger.warning(f"⚠️ User {auth_user_id} not found for permission revocation")

        # ==========================
        # DOCUMENT VERIFICATION SYNC
        # ==========================
        elif event_type == "ADMIN.DOCUMENT.VERIFIED":
            doc_id = data.get("document_id")
            status = data.get("status")
            reason = data.get("rejection_reason")
            
            if doc_id:
                from provider_dynamic_fields.models import ProviderDocument
                updated_count = ProviderDocument.objects.filter(id=doc_id).update(
                    status=status,
                    notes=reason
                )
                if updated_count:
                    logger.info(f"✅ Document {doc_id} verified: {status}")
                else:
                    logger.warning(f"⚠️ Document {doc_id} not found for verification update")

        else:
            logger.warning(f"⚠️ Unknown event type '{event_type}' received.")

    except Exception as e:
        logger.exception(f"❌ Error processing message: {e}")
