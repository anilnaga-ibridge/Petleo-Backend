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
        event_type = (event.get("event_type") or event.get("event") or "").upper()
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
                # Use auth_user_id as the lookup field (it's unique)
                user, created = VerifiedUser.objects.update_or_create(
                    auth_user_id=auth_user_id, 
                    defaults={
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
        elif event_type == "PROVIDER.PERMISSIONS.UPDATED":
            auth_user_id = data.get("auth_user_id") or data.get("data", {}).get("auth_user_id")
            permissions_list = data.get("permissions") or data.get("data", {}).get("permissions", [])
            templates = data.get("templates") or data.get("data", {}).get("templates", {})
            
            if auth_user_id:
                try:
                    user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
                    
                    # Import models here to avoid circular imports

                    from provider_dynamic_fields.models import (
                        ProviderTemplateService,
                        ProviderTemplateCategory,
                        ProviderTemplateFacility,
                        ProviderTemplatePricing,
                        ProviderCapabilityAccess
                    )
                    
                    with transaction.atomic():
                        # 1. SYNC TEMPLATES (If provided)
                        if templates:
                            # 1. DELETE OLD TEMPLATES (Global Wipe as per requirement)
                            logger.info("🗑️ Deleting old templates before sync...")
                            ProviderTemplatePricing.objects.all().delete()
                            ProviderTemplateFacility.objects.all().delete()
                            ProviderTemplateCategory.objects.all().delete()
                            ProviderTemplateService.objects.all().delete()

                            with open("consumer_debug.log", "a") as f:
                                f.write(f"Received Templates for {auth_user_id}: S={len(templates.get('services', []))}, C={len(templates.get('categories', []))}, F={len(templates.get('facilities', []))}, P={len(templates.get('pricing', []))}\n")
                            
                            # Services
                            count_services = len(templates.get("services", []))
                            print(f"Saving template services: {count_services}")
                            logger.info(f"Saving {count_services} template services...")
                            for svc in templates.get("services", []):
                                ProviderTemplateService.objects.update_or_create(
                                    super_admin_service_id=svc["id"],
                                    defaults={
                                        "name": svc["name"],
                                        "display_name": svc["display_name"],
                                        "icon": svc.get("icon", "tabler-box")
                                    }
                                )
                            
                            # Categories
                            count_categories = len(templates.get("categories", []))
                            print(f"Saving template categories: {count_categories}")
                            logger.info(f"Saving {count_categories} template categories...")
                            for cat in templates.get("categories", []):
                                try:
                                    service_obj = ProviderTemplateService.objects.get(super_admin_service_id=cat["service_id"])
                                    ProviderTemplateCategory.objects.update_or_create(
                                        super_admin_category_id=cat["id"],
                                        defaults={
                                            "service": service_obj,
                                            "name": cat["name"]
                                        }
                                    )
                                except ProviderTemplateService.DoesNotExist:
                                    logger.warning(f"⚠️ Service {cat['service_id']} not found for category {cat['name']}")

                            # Facilities
                            count_facilities = len(templates.get("facilities", []))
                            print(f"Saving template facilities: {count_facilities}")
                            logger.info(f"Saving {count_facilities} template facilities...")
                            for fac in templates.get("facilities", []):
                                try:
                                    cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=fac["category_id"])
                                    ProviderTemplateFacility.objects.update_or_create(
                                        super_admin_facility_id=fac["id"],
                                        defaults={
                                            "category": cat_obj,
                                            "name": fac["name"],
                                            "description": fac.get("description", "")
                                        }
                                    )
                                except ProviderTemplateCategory.DoesNotExist:
                                    logger.warning(f"⚠️ Category {fac['category_id']} not found for facility {fac['name']}")

                            # Pricing
                            count_pricing = len(templates.get("pricing", []))
                            print(f"Saving template pricing: {count_pricing}")
                            logger.info(f"Saving {count_pricing} template pricing rules...")
                            for price in templates.get("pricing", []):
                                try:
                                    service_obj = ProviderTemplateService.objects.get(super_admin_service_id=price["service_id"])
                                    
                                    cat_obj = None
                                    if price.get("category_id"):
                                        cat_obj = ProviderTemplateCategory.objects.filter(super_admin_category_id=price["category_id"]).first()
                                    
                                    fac_obj = None
                                    if price.get("facility_id"):
                                        fac_obj = ProviderTemplateFacility.objects.filter(super_admin_facility_id=price["facility_id"]).first()

                                    ProviderTemplatePricing.objects.update_or_create(
                                        super_admin_pricing_id=price["id"],
                                        defaults={
                                            "service": service_obj,
                                            "category": cat_obj,
                                            "facility": fac_obj,
                                            "price": price["price"],
                                            "duration": price["duration"],
                                            "description": price.get("description", "")
                                        }
                                    )
                                except ProviderTemplateService.DoesNotExist:
                                    logger.warning(f"⚠️ Service {price['service_id']} not found for pricing {price['id']}")

                            logger.info(f"✅ Synced Templates for user {auth_user_id}")

                        # 2. SYNC PERMISSIONS (ProviderCapabilityAccess)
                        # Clear existing permissions
                        ProviderCapabilityAccess.objects.filter(user=user).delete()
                        
                        # Create new permissions
                        new_perms = []
                        plan_id = data.get("purchased_plan", {}).get("plan_id")
                        
                        for perm in permissions_list:
                            new_perms.append(ProviderCapabilityAccess(
                                user=user,
                                plan_id=plan_id,
                                service_id=perm.get("service_id"),
                                category_id=perm.get("category_id"),
                                facility_id=perm.get("facility_id"),
                                can_view=perm.get("can_view", False),
                                can_create=perm.get("can_create", False),
                                can_edit=perm.get("can_edit", False),
                                can_delete=perm.get("can_delete", False),
                            ))
                        
                        if new_perms:
                            ProviderCapabilityAccess.objects.bulk_create(new_perms)
                            
                    logger.info(f"✅ Updated {len(new_perms)} capabilities for user {auth_user_id}")
                    
                except VerifiedUser.DoesNotExist:
                    logger.warning(f"⚠️ User {auth_user_id} not found for permission update")
                except Exception as e:
                    logger.error(f"❌ Error updating permissions for {auth_user_id}: {e}")

        elif event_type == "PROVIDER.PERMISSIONS.REVOKED":
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
            logger.info(f"🔍 RAW EVENT: {event}")

    except Exception as e:
        logger.exception(f"❌ Error processing message: {e}")
