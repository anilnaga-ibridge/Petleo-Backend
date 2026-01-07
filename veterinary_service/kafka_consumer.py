
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

        if event_type in ["USER_CREATED", "USER_UPDATED", "USER_VERIFIED"]:
            auth_user_id = data.get("auth_user_id") or data.get("id")
            role = (data.get("role") or "").lower()
            
            # Sync PetOwner (existing logic)
            if auth_user_id and event_type == "USER_UPDATED":
                owners = PetOwner.objects.filter(auth_user_id=auth_user_id)
                for owner in owners:
                    owner.first_name = data.get("first_name", owner.first_name)
                    owner.last_name = data.get("last_name", owner.last_name)
                    owner.email = data.get("email", owner.email)
                    owner.phone = data.get("phone", owner.phone)
                    owner.save()
                    logger.info(f"✅ Updated PetOwner {owner.id} from Auth User {auth_user_id}")

            # Sync VeterinaryStaff (NEW)
            if auth_user_id:
                from veterinary.models import VeterinaryStaff, Clinic
                
                # Try to link clinic if organization_id is present
                clinic = None
                org_id = data.get("organization_id")
                if org_id:
                     clinic = Clinic.objects.filter(provider_id=org_id).first()
                
                # If individual, they are their own clinic (provider_id = auth_user_id)
                if role == "individual":
                     clinic = Clinic.objects.filter(provider_id=auth_user_id).first()

                VeterinaryStaff.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "role": role,
                        "clinic": clinic
                    }
                )
                logger.info(f"✅ Synced VeterinaryStaff {auth_user_id} ({role})")

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

        elif event_type == "PROVIDER.PERMISSIONS.UPDATED":
            auth_user_id = data.get("auth_user_id")
            permissions_list = data.get("permissions", [])
            
            if auth_user_id:
                from veterinary.models import VeterinaryStaff
                
                # Extract capability strings from the complex permission objects
                capability_keys = set()
                for perm in permissions_list:
                    # 1. Check for explicit 'linked_capability' (New Standard)
                    cap = perm.get("linked_capability")
                    if cap:
                        capability_keys.add(cap)
                    
                    # 2. Fallback: Check for service_key or other identifiers if needed
                    # (For now, we rely on linked_capability being populated by Super Admin)

                if capability_keys:
                    # Update VeterinaryStaff permissions
                    # We use update_or_create to ensure it exists (though USER_CREATED should have created it)
                    # Note: We append to existing permissions or overwrite? 
                    # Overwriting is safer for "Sync" logic to remove revoked permissions.
                    
                    staff, created = VeterinaryStaff.objects.update_or_create(
                        auth_user_id=auth_user_id,
                        defaults={
                            "permissions": list(capability_keys)
                        }
                    )
                    logger.info(f"✅ Synced VeterinaryStaff Permissions for {auth_user_id}: {capability_keys}")
                else:
                    logger.info(f"ℹ️ No linked capabilities found for {auth_user_id}")
        elif event_type == "USER_PERMISSIONS_SYNCED":
            auth_user_id = data.get("auth_user_id")
            permissions_list = data.get("permissions", [])
            
            if auth_user_id:
                from veterinary.models import VeterinaryStaff
                
                # permissions_list is a list of dicts: [{ "service_key": "VETERINARY_VITALS", ... }]
                # We need to extract the keys (slugs) to store in VeterinaryStaff.permissions
                
                capability_keys = []
                for perm in permissions_list:
                    # Check for service_key first (new standard), fallback to service_name or id
                    key = perm.get("service_key") or perm.get("service_id")
                    if key:
                        capability_keys.append(key)
                        
                # Update VeterinaryStaff
                # We use update_or_create to ensure it exists
                VeterinaryStaff.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "permissions": capability_keys
                    }
                )
                logger.info(f"✅ Synced Permissions for {auth_user_id}: {len(capability_keys)} capabilities")

    except Exception as e:
        logger.exception(f"❌ Error processing Kafka message: {e}")
