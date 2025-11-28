# kafka/handlers.py
import logging
from django.db import transaction

from .consumer import GlobalKafkaConsumer
from service_provider.models import VerifiedUser
from provider_dynamic.models import LocalFieldDefinition

logger = logging.getLogger(__name__)

# ==========================================
# 🔹 HANDLER 1 — VERIFIED USER EVENTS
# ==========================================

@GlobalKafkaConsumer.register_handler("USER_CREATED")
@GlobalKafkaConsumer.register_handler("USER_VERIFIED")
def handle_user_created(payload):
    auth_id = payload.get("auth_user_id")
    if not auth_id:
        return

    with transaction.atomic():
        obj, created = VerifiedUser.objects.update_or_create(
            auth_user_id=auth_id,
            defaults={
                "full_name": payload.get("full_name"),
                "email": payload.get("email"),
                "phone_number": payload.get("phone_number"),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", []),
            },
        )

        logger.info(f"👤 VerifiedUser {'created' if created else 'updated'} → {obj.email}")


@GlobalKafkaConsumer.register_handler("USER_UPDATED")
def handle_user_updated(payload):
    auth_id = payload.get("auth_user_id")
    if not auth_id:
        return

    updated = VerifiedUser.objects.filter(auth_user_id=auth_id).update(
        full_name=payload.get("full_name"),
        email=payload.get("email"),
        phone_number=payload.get("phone_number"),
        role=payload.get("role"),
    )
    logger.info(f"🔄 USER_UPDATED → {updated}")


@GlobalKafkaConsumer.register_handler("USER_DELETED")
def handle_user_deleted(payload):
    auth_id = payload.get("auth_user_id")
    if not auth_id:
        return

    deleted, _ = VerifiedUser.objects.filter(auth_user_id=auth_id).delete()
    logger.info(f"🗑 USER_DELETED → {deleted}")

# ==========================================
# 🔹 HANDLER 2 — DYNAMIC FIELD EVENTS
# ==========================================

@GlobalKafkaConsumer.register_handler("created")
@GlobalKafkaConsumer.register_handler("updated")
def handle_field_upsert(payload):
    field_id = payload.get("id")
    if not field_id:
        return

    obj, created = LocalFieldDefinition.objects.update_or_create(
        id=field_id,
        defaults={
            "target": payload.get("target"),
            "name": payload.get("name"),
            "label": payload.get("label"),
            "field_type": payload.get("field_type"),
            "is_required": payload.get("is_required", False),
            "options": payload.get("options", []),
            "order": payload.get("order", 0),
            "help_text": payload.get("help_text"),
            "created_at": payload.get("created_at"),
        },
    )

    logger.info(f"📌 Field {'created' if created else 'updated'} → {obj.label}")


@GlobalKafkaConsumer.register_handler("deleted")
def handle_field_deleted(payload):
    field_id = payload.get("id")
    if not field_id:
        return

    LocalFieldDefinition.objects.filter(id=field_id).delete()
    logger.info(f"🗑 Field Deleted → {field_id}")
