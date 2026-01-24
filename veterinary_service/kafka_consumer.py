
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

from veterinary.models import PetOwner, VeterinaryStaff, Clinic, StaffClinicAssignment

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
            org_id = data.get("organization_id")

            # 1. Explicit Clinic Onboarding for Providers (Org or Individual)
            if role in ["organization", "individual"] and (event_type == "USER_CREATED" or event_type == "USER_VERIFIED"):
                clinic, created = Clinic.objects.get_or_create(
                    organization_id=auth_user_id,
                    defaults={
                        "name": f"Clinic - {data.get('full_name', auth_user_id)}",
                        "is_primary": True
                    }
                )
                if created:
                    logger.info(f"✨ Explicitly created Primary Clinic for {role} {auth_user_id}")
                elif not clinic.is_primary:
                    clinic.is_primary = True
                    clinic.save()
            
            # 2. Sync PetOwner (existing logic)
            if auth_user_id and event_type == "USER_UPDATED" and role == "customer":
                owners = PetOwner.objects.filter(auth_user_id=auth_user_id)
                for owner in owners:
                    owner.name = data.get("full_name", owner.name)
                    owner.email = data.get("email", owner.email)
                    owner.phone = data.get("phone_number", owner.phone)
                    owner.save()
                    logger.info(f"✅ Updated PetOwner {owner.id} from Auth User {auth_user_id}")

            # 3. Sync VeterinaryStaff & Assignments
            if auth_user_id and role not in ["customer", "organization"]:
                # Extract permissions from payload if present

                permissions = data.get("permissions", [])
                
                clinic = None
                if org_id:
                     # Find the primary clinic for the organization
                     clinic = Clinic.objects.filter(organization_id=org_id, is_primary=True).first()
                elif role == "individual":
                     # For individuals, they are their own organization
                     clinic = Clinic.objects.filter(organization_id=auth_user_id, is_primary=True).first()
                
                staff, _ = VeterinaryStaff.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "role": role,
                        "clinic": clinic,
                        "permissions": permissions  # [FIX] Save permissions to Staff
                    }
                )

                # Auto-create assignment to the primary clinic
                if clinic:
                    assignment, a_created = StaffClinicAssignment.objects.get_or_create(
                        staff=staff,
                        clinic=clinic,
                        defaults={
                            "role": role,
                            "permissions": permissions,  # [FIX] Use payload permissions explicitly
                            "is_primary": True,
                            "is_active": True
                        }
                    )
                    
                    # Ensure is_active is set
                    if not a_created and not assignment.is_active:
                         assignment.is_active = True
                         assignment.save()

                    if a_created:
                        logger.info(f"🔗 Created StaffClinicAssignment for {auth_user_id} @ {clinic.name} with {len(permissions)} perms")
                    if a_created:
                        logger.info(f"🔗 Created StaffClinicAssignment for {auth_user_id} @ {clinic.name}")

                logger.info(f"✅ Synced VeterinaryStaff {auth_user_id} ({role})")

        elif event_type == "PROVIDER_CAPABILITY_UPDATED":
            provider_id = data.get("provider_id")
            capabilities = data.get("capabilities", {})
            if provider_id:
                # Update all clinics belonging to this organization
                clinics = Clinic.objects.filter(organization_id=provider_id)
                count = clinics.update(capabilities=capabilities)
                if count > 0:
                    logger.info(f"✅ Updated Capabilities for {count} Clinics of Provider {provider_id}")
                else:
                    logger.warning(f"⚠️ No Clinics found for Provider {provider_id} - Skipping capability update")

        elif event_type == "PROVIDER.PERMISSIONS.UPDATED":
            auth_user_id = data.get("auth_user_id")
            permissions_list = data.get("permissions", [])
            
            if auth_user_id:
                
                # Extract capability strings from the complex permission objects
                capability_keys = set()
                for perm in permissions_list:
                    # 1. Check for explicit 'linked_capability' (New Standard)
                    cap = perm.get("linked_capability")
                    if cap:
                        capability_keys.add(cap)
                    
                    # 2. Fallback: Check for service_key or other identifiers if needed
                    # (For now, we rely on linked_capability being populated by Super Admin)

                # NEW: Extract Dynamic Capabilities
                dynamic_caps = data.get("dynamic_capabilities") or data.get("data", {}).get("dynamic_capabilities", [])
                for dc in dynamic_caps:
                     if dc.get("capability_key"):
                         capability_keys.add(dc.get("capability_key"))

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
                    
                    # Sync to assignments
                    StaffClinicAssignment.objects.filter(staff=staff, is_primary=True).update(permissions=list(capability_keys))
                    
                    logger.info(f"✅ Synced VeterinaryStaff Permissions for {auth_user_id}: {capability_keys}")
                else:
                    logger.info(f"ℹ️ No linked capabilities found for {auth_user_id}")
                    
        elif event_type == "USER_PERMISSIONS_SYNCED":
            auth_user_id = data.get("auth_user_id")
            permissions_list = data.get("permissions", [])
            
            if auth_user_id:
                
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
                staff, _ = VeterinaryStaff.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "permissions": capability_keys
                    }
                )
                
                # Sync to assignments
                StaffClinicAssignment.objects.filter(staff=staff, is_primary=True).update(permissions=capability_keys)
                
                # [FIX] Sync to Clinic Capabilities if user is an Organization Owner
                # This ensures the sidebar (which reads from Clinic.capabilities) works for the admin
                role = (data.get("role") or "").lower()
                if role in ["organization", "individual", "provider", "organization_provider"]:
                    clinics = Clinic.objects.filter(organization_id=auth_user_id)
                    clinics.update(capabilities={"permissions": capability_keys})
                    logger.info(f"🏥 Synced Clinic Capabilities for Org Owner {auth_user_id}")

                logger.info(f"✅ Synced Permissions for {auth_user_id}: {len(capability_keys)} capabilities")

    except Exception as e:
        logger.exception(f"❌ Error processing Kafka message: {e}")
