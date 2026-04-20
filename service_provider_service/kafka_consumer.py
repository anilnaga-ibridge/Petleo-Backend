import os
import json
import django
import logging
import time
from kafka import KafkaConsumer
from django.db import transaction
from django.utils import timezone

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee, ServiceProvider
from provider_dynamic_fields.models import LocalFieldDefinition, LocalDocumentDefinition, ProviderDocument
from service_provider.role_capabilities import get_default_capabilities

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("kafka").setLevel(logging.CRITICAL)
logger = logging.getLogger("service_provider_consumer")
# Add File Handler
fh = logging.FileHandler("debug_consumer.txt")
fh.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info("🚀 Starting Service Provider Unified Kafka Consumer...")

# Kafka init (retry loop)
consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            "individual_events",
            "organization_events",
            "admin_events",
            "service_provider_events",
            "booking_events",
            "provider_permissions_events",
            bootstrap_servers="localhost:9093",
            group_id="service-provider-group",
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
        service = event.get("service")
        perms_map = {} # Initialize early
        
        logger.info(f"🔥 Event: {event_type} | Role: {role} | Service: {service}")

        # logger.info(f"🔥 Event: {event_type} | Role: {role} | Service: {service}")
        
        # [MODIFIED] Do NOT skip admin/super_admin anymore. 
        # We need their VerifiedUser record to stay in sync for Account Settings.

        # ==========================
        # PERMISSION SYNC EVENTS
        # ==========================
        # ==========================
        # PERMISSION SYNC EVENTS (Canonical Path)
        # ==========================
        if event_type == "PROVIDER.PERMISSIONS.UPDATED":
            logger.info(f"🔑 Processing Permission Sync Event: {event.get('event_id')}")
            try:
                from service_provider.kafka.permission_consumer import PermissionSyncConsumer
                
                # Consistently use 'admin_events' as the source for idempotency tracking
                sync_handler = PermissionSyncConsumer(topic="admin_events")
                sync_handler.process(event)
                logger.info("   ✅ Finished processing Permission Sync Event.")
            except Exception as sync_err:
                logger.error(f"   ❌ SYNC ERROR: {sync_err}")
                import traceback
                logger.error(traceback.format_exc())
            continue
            
        # ==========================
        # USER EVENTS
        # ==========================
        if event_type in ["USER_CREATED", "USER_VERIFIED"]:
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id:
                logger.warning("⚠️ Missing auth_user_id, skipping")
                continue

            # ==========================
            # EMPLOYEE FLOW (ONLY ORG EMPLOYEES)
            # ==========================
            logger.info(f"DEBUG: Checking role '{role}' against employee list...")
            if role in ["employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "lab tech", "pharmacy", "vitalsstaff", "vitals staff"]:
                logger.info("DEBUG: Role matched employee list.")
                organization_id = data.get("organization_id")
                # For USER_VERIFIED, organization_id might not be in payload, so we rely on existing record
                # But for USER_CREATED it is mandatory.
                
                if event_type == "USER_CREATED":
                    if not organization_id:
                        logger.error(f"❌ Employee {auth_user_id} missing organization_id in USER_CREATED")
                        continue
                    
                    logger.info(f"🔍 Processing Employee {auth_user_id} for Org {organization_id}")
                    
                    try:
                        org_provider = ServiceProvider.objects.get(
                            verified_user__auth_user_id=organization_id
                        )
                        
                        employee, created = OrganizationEmployee.objects.get_or_create(
                            auth_user_id=auth_user_id,
                            defaults={
                                "organization": org_provider,
                                "full_name": data.get("full_name"),
                                "email": data.get("email"),
                                "phone_number": data.get("phone_number"),
                                "role": role,
                                "status": "PENDING",
                                "created_by": data.get("created_by"),
                                "average_rating": 0.0,
                                "total_ratings": 0
                            }
                        )
                        if not created:
                            # Update fields but do NOT overwrite status to PENDING
                            employee.organization = org_provider
                            employee.full_name = data.get("full_name") or employee.full_name
                            employee.email = data.get("email") or employee.email
                            employee.phone_number = data.get("phone_number") or employee.phone_number
                            employee.role = role or employee.role
                            employee.created_by = data.get("created_by") or employee.created_by
                            employee.save()
                        logger.info(f"✅ Created OrganizationEmployee {auth_user_id} (Invited)")
                        
                    except ServiceProvider.DoesNotExist:
                        # Try to recover by creating the provider profile if the user exists
                        try:
                            org_user = VerifiedUser.objects.get(auth_user_id=organization_id)
                            org_provider, _ = ServiceProvider.objects.get_or_create(verified_user=org_user)
                            logger.info(f"✅ Recovered/Created ServiceProvider for {organization_id}")
                            
                            # Retry creation
                            employee, created = OrganizationEmployee.objects.get_or_create(
                                auth_user_id=auth_user_id,
                                defaults={
                                    "organization": org_provider,
                                    "full_name": data.get("full_name"),
                                    "email": data.get("email"),
                                    "phone_number": data.get("phone_number"),
                                    "role": role,
                                    "status": "PENDING",
                                    "created_by": data.get("created_by"),
                                    "average_rating": 0.0,
                                    "total_ratings": 0
                                }
                            )
                            if not created:
                                employee.organization = org_provider
                                employee.full_name = data.get("full_name") or employee.full_name
                                employee.email = data.get("email") or employee.email
                                employee.phone_number = data.get("phone_number") or employee.phone_number
                                employee.role = role or employee.role
                                employee.created_by = data.get("created_by") or employee.created_by
                                employee.save()
                            logger.info(f"✅ Created OrganizationEmployee {auth_user_id} (Invited) after recovery")
                            
                        except VerifiedUser.DoesNotExist:
                            logger.error(f"❌ Organization User {organization_id} not found. Cannot create employee.")
                            continue

                elif event_type == "USER_VERIFIED":
                    try:
                        employee = OrganizationEmployee.objects.get(auth_user_id=auth_user_id)
                        employee.status = "ACTIVE"
                        employee.joined_at = timezone.now()
                        employee.full_name = data.get("full_name", employee.full_name)
                        employee.email = data.get("email", employee.email)
                        employee.phone_number = data.get("phone_number", employee.phone_number)
                        employee.save()
                        logger.info(f"✅ Activated OrganizationEmployee {auth_user_id}")
                    except OrganizationEmployee.DoesNotExist:
                        logger.warning(f"⚠️ Employee {auth_user_id} not found for activation")

            # ==========================
            # VERIFIED USER SYNC (ALL ROLES)
            # ==========================
            if role in ["individual", "organization", "serviceprovider", "provider", "petowner", "pet_owner", "employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "lab tech", "pharmacy", "vitalsstaff", "vitals staff", "superadmin", "super_admin", "admin"]:
                with transaction.atomic():
                    # Handle 'provider' as 'organization' for backward compatibility or generic events
                    actual_role = role
                    if role == "provider":
                        actual_role = "organization"

                    user, created = VerifiedUser.objects.update_or_create(
                        auth_user_id=auth_user_id,
                        defaults={
                            "full_name": data.get("full_name"),
                            "email": data.get("email"),
                            "phone_number": data.get("phone_number"),
                            "role": actual_role,
                            "avatar_url": data.get("avatar_url"),
                            "permissions": get_default_capabilities(actual_role),
                        },
                    )
                    logger.info(
                        f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser {user.email}"
                    )
                    
                    # Auto-create ServiceProvider profile for organizations and individuals
                    if actual_role in ["organization", "serviceprovider", "provider"]:
                        provider, p_created = ServiceProvider.objects.update_or_create(
                            verified_user=user,
                            defaults={"provider_type": "ORGANIZATION"}
                        )
                        if p_created:
                            logger.info(f"✅ Auto-created ServiceProvider profile (ORGANIZATION) for {user.email}")
                        else:
                            logger.info(f"🔄 Updated ServiceProvider provider_type to ORGANIZATION for {user.email}")
                    elif role == "individual":
                        provider, p_created = ServiceProvider.objects.update_or_create(
                            verified_user=user,
                            defaults={"provider_type": "INDIVIDUAL"}
                        )
                        if p_created:
                            logger.info(f"✅ Auto-created ServiceProvider profile (INDIVIDUAL) for {user.email}")

        elif event_type == "EMPLOYEE_UPDATED":
            auth_user_id = data.get("auth_user_id")
            if auth_user_id:
                updated_count = OrganizationEmployee.objects.filter(auth_user_id=auth_user_id).update(
                    full_name=data.get("full_name"),
                    email=data.get("email"),
                    phone_number=data.get("phone_number"),
                    role=role or data.get("role")
                )
                if updated_count:
                    logger.info(f"🆙 Updated OrganizationEmployee {auth_user_id}")
                else:
                    logger.warning(f"⚠️ OrganizationEmployee {auth_user_id} not found for update")

        # ==========================
        # USER UPDATED (ALL ROLES)
        # ==========================
        elif event_type == "USER_UPDATED":
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id:
                continue

            # [FIX] Use update_or_create for robustness, especially for SuperAdmins
            if role in ["superadmin", "super_admin", "admin"]:
                user, created = VerifiedUser.objects.update_or_create(
                    auth_user_id=auth_user_id,
                    defaults={
                        "full_name": data.get("full_name"),
                        "email": data.get("email"),
                        "phone_number": data.get("phone_number"),
                        "role": role,
                        "avatar_url": data.get("avatar_url"),
                    }
                )
                if created:
                    logger.info(f"✅ JIT Created VerifiedUser via UPDATED event: {auth_user_id}")
                else:
                    logger.info(f"🆙 Updated VerifiedUser {auth_user_id}")
            else:
                # [FIX] Protect role field — don't let 'provider' or empty role overwrite specific values
                update_fields = {
                    "full_name": data.get("full_name"),
                    "email": data.get("email"),
                    "phone_number": data.get("phone_number"),
                    "avatar_url": data.get("avatar_url"),
                }
                
                # Only update role if it's a specific, valid role
                if role and role not in ["provider", "serviceprovider"]:
                    update_fields["role"] = role
                
                updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(**update_fields)
                if updated:
                    logger.info(f"🆙 Updated VerifiedUser {auth_user_id}")
                
            # Also update Employee record if it exists
            OrganizationEmployee.objects.filter(auth_user_id=auth_user_id).update(
                full_name=data.get("full_name"),
                email=data.get("email"),
                phone_number=data.get("phone_number"),
                role=role
            )

        # ==========================
        # USER DELETED
        # ==========================
        elif event_type == "USER_DELETED":
            auth_user_id = data.get("auth_user_id")
            if not auth_user_id:
                continue

            VerifiedUser.objects.filter(auth_user_id=auth_user_id).delete()
            OrganizationEmployee.objects.filter(auth_user_id=auth_user_id).delete()
            logger.info(f"🗑️ Deleted user records for {auth_user_id}")

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
                updated_count = ProviderDocument.objects.filter(id=doc_id).update(
                    status=status,
                    notes=reason
                )
                if updated_count:
                    logger.info(f"✅ Document {doc_id} verified: {status}")
                else:
                    logger.warning(f"⚠️ Document {doc_id} not found for verification update")

        # ==========================
        # PLAN STATUS SYNC
        # ==========================
        elif event_type == "PLAN.STATUS.CHANGED":
            plan_id = data.get("plan_id")
            is_active = data.get("is_active", False)
            
            if plan_id:
                from service_provider.models import ProviderSubscription
                
                with transaction.atomic():
                    # Update all subscriptions for this plan
                    updated_count = ProviderSubscription.objects.filter(plan_id=plan_id).update(is_active=is_active)
                    logger.info(f"🔄 Plan {plan_id} status changed to {is_active}. Updated {updated_count} subscriptions.")

        # ==========================
        # BOOKING EVENTS
        # ==========================
        elif event_type == "BOOKING_CREATED":
            from service_provider.notifications import handle_booking_created_notification
            handle_booking_created_notification(data)


        else:
            logger.warning(f"⚠️ Unknown event type '{event_type}' received.")

    except Exception as e:
        logger.exception(f"❌ Error processing Kafka message: {e}")
