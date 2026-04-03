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
            "veterinary_events",
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

# Import models inside the loop or at setup to ensure they are loaded
from pets.models import Pet, PetDocument, PetVaccination

for message in consumer:
    try:
        event = message.value
        event_type = (event.get("event_type") or "").upper()
        data = event.get("data") or {}
        
        # Handle User/Owner Events
        if event_type in ["USER_CREATED", "USER_VERIFIED", "USER_UPDATED", "USER_DELETED"]:
            role = (event.get("role") or data.get("role") or "").lower()
            if role not in ["petowner", "pet_owner", "pet owner", "customer"]:
                continue
            
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id:
                continue

            logger.info(f"🔥 User Event: {event_type} | User: {auth_user_id}")

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
                    logger.info(f"{'✅ Created' if created else '🔄 Updated'} PetOwnerProfile for {auth_user_id}")

            elif event_type == "USER_DELETED":
                PetOwnerProfile.objects.filter(auth_user_id=auth_user_id).delete()
                logger.info(f"🗑️ Deleted PetOwnerProfile for {auth_user_id}")

        # Handle Veterinary Events (Medical Record Sync)
        elif event_type.startswith("VET_"):
            pet_id = data.get("pet_external_id") or data.get("pet_id")
            if not pet_id:
                continue

            logger.info(f"🏥 Veterinary Event: {event_type} | Pet: {pet_id}")
            
            try:
                pet = Pet.objects.get(id=pet_id)
            except Pet.DoesNotExist:
                logger.warning(f"⚠️ Pet {pet_id} not found in customer service. Skipping sync.")
                continue

            with transaction.atomic():
                if event_type == "VET_LAB_RESULT_PUBLISHED":
                    results_text = "\n".join([f"{r['field']}: {r['value']} {r.get('unit', '')} ({r['flag']})" for r in data.get('results', [])])
                    PetDocument.objects.create(
                        pet=pet,
                        document_name=f"Lab Report: {data.get('template_name', 'General')}",
                        document_type='DIAGNOSTIC_REPORT',
                        uploaded_by='PROVIDER',
                        verified_at=timezone.now(),
                        file_type='text/plain' # Virtual document for now
                    )
                    logger.info(f"📊 Synced Lab Result for Pet {pet.name}")

                elif event_type == "VET_PRESCRIPTION_CREATED":
                    PetDocument.objects.create(
                        pet=pet,
                        document_name=f"Prescription: {data.get('medicine_name', 'Medication')}",
                        document_type='PRESCRIPTION',
                        uploaded_by='PROVIDER',
                        verified_at=timezone.now(),
                        file_type='text/plain'
                    )
                    logger.info(f"💊 Synced Prescription for Pet {pet.name}")

                elif event_type == "VET_VACCINATION_RECORDED":
                    PetVaccination.objects.create(
                        pet=pet,
                        vaccine_name=data.get("vaccine_name"),
                        date_administered=data.get("date_given"),
                        next_due_date=data.get("next_due_date"),
                        administered_by="Veterinary Clinician",
                        notes=f"Synced from Veterinary Service (ID: {data.get('vaccination_id')})"
                    )
                    logger.info(f"💉 Synced Vaccination for Pet {pet.name}")

                elif event_type == "VET_VISIT_SUMMARY_PUBLISHED":
                    PetDocument.objects.create(
                        pet=pet,
                        document_name=f"Visit Summary: {data.get('clinic_name', 'Clinic')}",
                        document_type='MEDICAL_REPORT',
                        uploaded_by='PROVIDER',
                        verified_at=timezone.now(),
                        file_type='text/plain'
                    )
                    logger.info(f"📝 Synced Visit Summary for Pet {pet.name}")

    except Exception as e:
        logger.error(f"❌ Error processing Kafka message: {e}")
