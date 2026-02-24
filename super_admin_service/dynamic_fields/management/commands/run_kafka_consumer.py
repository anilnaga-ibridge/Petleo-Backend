
from django.core.management.base import BaseCommand
import json
import logging
import time
from kafka import KafkaConsumer
from django.db import transaction
from django.conf import settings
from admin_core.models import VerifiedUser
from dynamic_fields.models import ProviderDocumentVerification

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Super Admin Kafka Consumer'

    def normalize_role(self, role):
        if not role:
            return None
        return str(role).replace(" ", "").replace("_", "").lower()

    def handle(self, *args, **options):
        logger.info("🚀 Starting SuperAdmin Kafka Consumer (Management Command)")
        logger.info(f"📁 DB: {settings.DATABASES['default']['NAME']}")

        consumer = None
        while not consumer:
            try:
                consumer = KafkaConsumer(
                    "service_provider_events",
                    "admin_events",
                    "organization_events",
                    "individual_events",
                    bootstrap_servers="localhost:9093",
                    group_id="superadmin-service-group",
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                )
                logger.info("✅ Kafka Connected")
                logger.info("📡 Listening to topics...")
            except Exception as e:
                logger.warning(f"⚠️ Kafka unavailable: {e}")
                logger.info("🔁 Retrying in 5 seconds...")
                time.sleep(5)

        logger.info("✅ Consumer ready. Waiting for messages...")

        for message in consumer:
            try:
                logger.info(f"RAW MESSAGE: {message.value}")
                event = message.value
                event_type = event.get("event_type", "").upper()
                data = event.get("data", {})
                raw_role = event.get("role")
                role = self.normalize_role(raw_role)

                logger.info(f"📨 EVENT: {event_type} | Role={role} | Data={data}")

                auth_user_id = data.get("auth_user_id")
                if not auth_user_id:
                    logger.warning("⚠️ Missing auth_user_id, skipping.")
                    continue

                if event_type in ["USER_CREATED", "ADMIN_CREATED", "SUPERADMIN_CREATED"]:
                    with transaction.atomic():
                        user, created = VerifiedUser.objects.update_or_create(
                            auth_user_id=auth_user_id,
                            defaults={
                                "full_name": data.get("full_name"),
                                "email": data.get("email"),
                                "phone_number": data.get("phone_number"),
                                "role": role,
                                "avatar_url": data.get("avatar_url"),
                                "permissions": data.get("permissions", []),
                            }
                        )
                        logger.info(f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser: {user.email}")

                elif event_type in ["USER_UPDATED", "EMPLOYEE_UPDATED"]:
                    updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
                        full_name=data.get("full_name"),
                        email=data.get("email"),
                        phone_number=data.get("phone_number"),
                        role=role,
                        avatar_url=data.get("avatar_url"),
                    )
                    if updated:
                        logger.info(f"🆙 Updated VerifiedUser: {data.get('email')}")
                    else:
                        logger.warning(f"⚠️ User not found: {auth_user_id}")

                elif event_type in ["USER_DELETED", "ADMIN_DELETED", "SUPERADMIN_DELETED"]:
                    deleted, _ = VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()
                    if deleted:
                        doc_deleted, _ = ProviderDocumentVerification.objects.filter(auth_user_id=auth_user_id).delete()
                        logger.info(f"🗑️ Deleted VerifiedUser ID={auth_user_id}. Included {doc_deleted} documents.")
                    else:
                        logger.warning(f"⚠️ User not found for deletion: {auth_user_id}")

                elif event_type == "PROVIDER.DOCUMENT.UPLOADED":
                    doc_id = data.get("document_id")
                    ProviderDocumentVerification.objects.update_or_create(
                        document_id=doc_id,
                        defaults={
                            "auth_user_id": data.get("auth_user_id"),
                            "definition_id": data.get("definition_id"),
                            "file_url": data.get("file_url"),
                            "filename": data.get("filename"),
                            "status": "pending"
                        }
                    )
                    logger.info(f"✅ Document Verification Synced: {data.get('filename')} (ID: {doc_id})")

            except Exception as e:
                logger.exception(f"❌ Error processing message: {e}")
