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
                        
                        OrganizationEmployee.objects.update_or_create(
                            auth_user_id=auth_user_id,
                            defaults={
                                "organization": org_provider,
                                "full_name": data.get("full_name"),
                                "email": data.get("email"),
                                "phone_number": data.get("phone_number"),
                                "role": role,
                                "status": "PENDING",
                                "created_by": data.get("created_by")
                            },
                        )
                        logger.info(f"✅ Created OrganizationEmployee {auth_user_id} (Invited)")
                        
                    except ServiceProvider.DoesNotExist:
                        # Try to recover by creating the provider profile if the user exists
                        try:
                            org_user = VerifiedUser.objects.get(auth_user_id=organization_id)
                            org_provider, _ = ServiceProvider.objects.get_or_create(verified_user=org_user)
                            logger.info(f"✅ Recovered/Created ServiceProvider for {organization_id}")
                            
                            # Retry creation
                            OrganizationEmployee.objects.update_or_create(
                                auth_user_id=auth_user_id,
                                defaults={
                                    "organization": org_provider,
                                    "full_name": data.get("full_name"),
                                    "email": data.get("email"),
                                    "phone_number": data.get("phone_number"),
                                    "role": role,
                                    "status": "PENDING",
                                    "created_by": data.get("created_by")
                                },
                            )
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
            if role in ["individual", "organization", "serviceprovider", "pet_owner", "employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "lab tech", "pharmacy", "vitalsstaff", "vitals staff", "superadmin", "super_admin", "admin"]:
                with transaction.atomic():
                    user, created = VerifiedUser.objects.update_or_create(
                        auth_user_id=auth_user_id,
                        defaults={
                            "full_name": data.get("full_name"),
                            "email": data.get("email"),
                            "phone_number": data.get("phone_number"),
                            "role": role,
                            "permissions": get_default_capabilities(role),
                        },
                    )
                    logger.info(
                        f"{'✅ Created' if created else '🔄 Updated'} VerifiedUser {user.email}"
                    )
                    
                    # Auto-create ServiceProvider profile for organizations
                    if role in ["organization", "serviceprovider"]:
                        provider, p_created = ServiceProvider.objects.get_or_create(verified_user=user)
                        if p_created:
                            logger.info(f"✅ Auto-created ServiceProvider profile for {user.email}")

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
        # USER UPDATED (NON-EMPLOYEE ONLY)
        # ==========================
        elif event_type == "USER_UPDATED":
            if role in ["employee", "receptionist", "veterinarian", "groomer", "doctor", "labtech", "pharmacy", "vitalsstaff"]:
                continue

            auth_user_id = data.get("auth_user_id")
            if not auth_user_id:
                continue

            updated = VerifiedUser.objects.filter(auth_user_id=auth_user_id).update(
                full_name=data.get("full_name"),
                email=data.get("email"),
                phone_number=data.get("phone_number"),
                role=role,
                permissions=get_default_capabilities(role),
            )
            if updated:
                logger.info(f"🆙 Updated VerifiedUser {auth_user_id}")

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
                    
                    logger.info(f"DEBUG: [KAFKA RECV] provider.permissions.updated | User: {auth_user_id}")
                    logger.info(f"DEBUG: Payload Keys: {list(data.keys())}")
                    if templates:
                        logger.info(f"DEBUG: Templates Received - Services: {len(templates.get('services', []))}, Cats: {len(templates.get('categories', []))}")
                    
                    # Import models here to avoid circular imports

                    from provider_dynamic_fields.models import (
                        ProviderTemplateService,
                        ProviderTemplateCategory,
                        ProviderTemplateFacility,
                        ProviderTemplatePricing,
                        ProviderCapabilityAccess
                    )
                    from service_provider.models import AllowedService
                    
                    with transaction.atomic():
                        # 1. SYNC TEMPLATES (If provided)
                        if templates:
                            # NOTE: Do NOT wipe templates globally. They are shared across all users.
                            # We use update_or_create to ensure we have the latest definitions.

                            # Services
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
                            for cat in templates.get("categories", []):
                                try:
                                    service_obj = ProviderTemplateService.objects.get(super_admin_service_id=cat["service_id"])
                                    ProviderTemplateCategory.objects.update_or_create(
                                        super_admin_category_id=cat["id"],
                                        defaults={
                                            "service": service_obj,
                                            "name": cat["name"],
                                            "linked_capability": cat.get("linked_capability")
                                        }
                                    )
                                except ProviderTemplateService.DoesNotExist:
                                    logger.warning(f"⚠️ Service {cat['service_id']} not found for category {cat['name']}")

                            # Facilities
                            for fac in templates.get("facilities", []):
                                try:
                                    cat_id = fac.get("category_id")
                                    if not cat_id:
                                        logger.warning(f"⏭️ Skipping facility {fac.get('name')} - missing category_id")
                                        continue
                                        
                                    cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=cat_id)
                                    ProviderTemplateFacility.objects.update_or_create(
                                        super_admin_facility_id=fac["id"],
                                        defaults={
                                            "category": cat_obj,
                                            "name": fac["name"],
                                            "description": fac.get("description", "")
                                        }
                                    )
                                except ProviderTemplateCategory.DoesNotExist:
                                    logger.warning(f"⚠️ Category {fac.get('category_id')} not found for facility {fac['name']}")

                            # Pricing
                            # Pricing
                            for price in templates.get("pricing", []):
                                try:
                                    service_obj = ProviderTemplateService.objects.get(super_admin_service_id=price["service_id"])
                                    
                                    # 1. Determine Target Facilities
                                    target_facilities = []
                                    
                                    explicit_fac_id = price.get("facility_id")
                                    cat_id = price.get("category_id")

                                    if explicit_fac_id:
                                        # CASE A: Explicit Facility Price
                                        fac_obj = ProviderTemplateFacility.objects.filter(super_admin_facility_id=explicit_fac_id).first()
                                        if fac_obj: 
                                            target_facilities.append((fac_obj, price["id"])) # Use original ID
                                        else:
                                             logger.warning(f"⚠️ Facility {explicit_fac_id} not found for pricing {price['id']}")

                                    elif cat_id:
                                        # CASE B: Category Level Price -> EXPLODE to all Facilities
                                        try:
                                            cat_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=cat_id)
                                            
                                            # 🛡️ CLEANUP: Delete existing pricing for this category to prevent duplicates
                                            # This handles the case where we re-explode and IDs might have shifted or old ones linger
                                            ProviderTemplatePricing.objects.filter(
                                                category=cat_obj, 
                                                service=service_obj
                                            ).delete()

                                            linked_facs = ProviderTemplateFacility.objects.filter(category=cat_obj)
                                            
                                            if not linked_facs.exists():
                                                logger.warning(f"⚠️ Pricing {price['id']} has Category {cat_id} but NO facilities exist to attach to.")
                                            
                                            for lf in linked_facs:
                                                # CRITICAL: Create Composite ID to satisfy unique=True constraint
                                                composite_id = f"{price['id']}_{lf.super_admin_facility_id}" 
                                                target_facilities.append((lf, composite_id))
                                                
                                            logger.info(f"💥 Exploded Category Price {price['id']} into {len(target_facilities)} facilities.")
                                            
                                        except ProviderTemplateCategory.DoesNotExist:
                                            logger.warning(f"⚠️ Category {cat_id} not found for pricing {price['id']}")

                                    else:
                                        logger.warning(f"⏭️ Skipping pricing {price['id']} - No Facility or Category linked.")
                                        continue

                                    # 2. Persist Rows
                                    for fac_obj, unique_sa_id in target_facilities:
                                        cat_obj = fac_obj.category
                                        
                                        # ⚠️ CRITICAL FIX #1: BILLING UNIT VALIDATION
                                        # Previously: duration field accepted null, causing NOT NULL violations
                                        # Now: Validate billing_unit and handle duration_minutes correctly
                                        billing_unit = price.get("billing_unit", "PER_SESSION")
                                        duration_minutes = price.get("duration_minutes")  # Can be None
                                        
                                        # Defensive validation: ensure billing_unit is valid
                                        VALID_BILLING_UNITS = ["HOURLY", "DAILY", "WEEKLY", "PER_SESSION", "ONE_TIME"]
                                        if billing_unit not in VALID_BILLING_UNITS:
                                            logger.warning(f"⚠️ Invalid billing_unit '{billing_unit}', defaulting to PER_SESSION")
                                            billing_unit = "PER_SESSION"
                                        
                                        # Log for transparency
                                        logger.debug(f"💰 Pricing: {fac_obj.name} = ₹{price['price']} ({billing_unit}, {duration_minutes}min)")

                                        ProviderTemplatePricing.objects.update_or_create(
                                            super_admin_pricing_id=unique_sa_id,
                                            defaults={
                                                "service": service_obj,
                                                "category": cat_obj,
                                                "facility": fac_obj,
                                                "price": price["price"],
                                                "billing_unit": billing_unit,
                                                "duration_minutes": duration_minutes,  # Explicitly None if not provided
                                                "description": price.get("description", "")
                                            }
                                        )

                                except ProviderTemplateService.DoesNotExist:
                                    logger.warning(f"⚠️ Service {price['service_id']} not found for pricing {price['id']}")

                            logger.info(f"✅ Synced Templates for user {auth_user_id}")

                        # 2. SYNC PERMISSIONS (ProviderCapabilityAccess)
                        plan_id = data.get("purchased_plan", {}).get("plan_id")
                        
                        # 🛡️ CRITICAL FIX #3: NEVER SET VETERINARY_CORE UNCONDITIONALLY
                        # ⚠️ WARNING: DO NOT CHANGE THIS TO user.permissions = ["VETERINARY_CORE"]
                        # That causes the Veterinary Dashboard to appear for ALL providers,
                        # even those without veterinary services.
                        # 
                        # Why empty list?
                        # - If transaction succeeds: permissions populated correctly later (line 581)
                        # - If transaction fails: user has NO permissions (safe state)
                        # - VETERINARY_CORE is ONLY added IF veterinary capabilities exist (line 577)
                        ProviderCapabilityAccess.objects.filter(user=user).delete()
                        AllowedService.objects.filter(verified_user=user).delete()
                        user.permissions = []  # ✅ Must start EMPTY
                        
                        logger.info(f"🧹 Cleared old permissions for user {auth_user_id} → permissions=[]")
                        
                        # Dictionary to track unique permissions: (service, category, facility, pricing) -> dict
                        perms_map = {}
                        
                        # Helper to add/update permission
                        def add_perm(s_id, c_id, f_id, p_id, **kwargs):
                            key = (s_id, c_id, f_id, p_id)
                            if key not in perms_map:
                                perms_map[key] = {
                                    "service_id": s_id,
                                    "category_id": c_id,
                                    "facility_id": f_id,
                                    "pricing_id": p_id,
                                    "can_view": True, 
                                    "can_create": False,
                                    "can_edit": False,
                                    "can_delete": False
                                }
                            perms_map[key].update(kwargs)

                        # A. Auto-generate from Templates (Robust Sync)
                        # 1. Services
                        for svc in templates.get("services", []):
                            add_perm(svc["id"], None, None, None)
                            
                        # 2. Categories
                        cat_service_map = {} 
                        for cat in templates.get("categories", []):
                            cat_service_map[cat["id"]] = cat["service_id"]
                            add_perm(cat["service_id"], cat["id"], None, None)
                            
                        # 3. Facilities
                        for fac in templates.get("facilities", []):
                            cat_id = fac.get("category_id")
                            if cat_id:
                                s_id = cat_service_map.get(cat_id)
                                if s_id:
                                    add_perm(s_id, cat_id, fac["id"], None)

                        # 4. Pricing
                        for price in templates.get("pricing", []):
                            # Strict Hierarchy: Price -> Facility -> Category -> Service
                            if not price.get("facility_id"):
                                continue

                            add_perm(
                                price["service_id"], 
                                price.get("category_id"), 
                                price.get("facility_id"), 
                                price["id"]
                            )

                        # B. Apply Explicit Permissions (Overrides)
                        for perm in permissions_list:
                            add_perm(
                                perm.get("service_id"),
                                perm.get("category_id"),
                                perm.get("facility_id"),
                                perm.get("pricing_id"),
                                can_view=perm.get("can_view", True),
                                can_create=perm.get("can_create", False),
                                can_edit=perm.get("can_edit", False),
                                can_delete=perm.get("can_delete", False)
                            )

                        # Create new permissions objects
                        logger.info(f"DEBUG: perms_map size: {len(perms_map)}")
                        if perms_map:
                            sample_keys = list(perms_map.keys())[:3]
                            logger.info(f"DEBUG: Sample perms_map keys: {sample_keys}")
                        
                        new_perms = []
                        for p_data in perms_map.values():
                            new_perms.append(ProviderCapabilityAccess(
                                user=user,
                                plan_id=plan_id,
                                service_id=p_data["service_id"],
                                category_id=p_data["category_id"],
                                facility_id=p_data["facility_id"],
                                pricing_id=p_data["pricing_id"],
                                can_view=p_data["can_view"],
                                can_create=p_data["can_create"],
                                can_edit=p_data["can_edit"],
                                can_delete=p_data["can_delete"],
                            ))
                        
                        logger.info(f"DEBUG: About to bulk_create {len(new_perms)} ProviderCapabilityAccess records")
                        if new_perms:
                            ProviderCapabilityAccess.objects.bulk_create(new_perms)
                            logger.info(f"DEBUG: bulk_create completed successfully")
                            
                            # 🛡️ Audit Log
                            from service_provider.models import PermissionAuditLog
                            PermissionAuditLog.log_action(
                                actor=None,
                                action='PLAN_SYNCED_KAFKA',
                                details={
                                    'plan_id': plan_id,
                                    'capability_count': len(new_perms),
                                    'user_email': user.email
                                }
                            )

                            # 🔄 Manual Cache Invalidation (signals don't trigger for bulk_create)
                            try:
                                provider_profile = user.provider_profile
                                for emp in provider_profile.employees.all():
                                    emp.invalidate_permission_cache()
                                logger.info(f"🗑️ Invalidated cache for {provider_profile.employees.count()} employees")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to invalidate cache: {e}")
                        
                        # REBUILD AllowedService from current plan
                        unique_allowed = {}
                        for svc_data in templates.get("services", []):
                            unique_allowed[svc_data["id"]] = {
                                "name": svc_data["display_name"],
                                "icon": svc_data.get("icon", "tabler-box")
                            }
                            
                        for s_id, s_meta in unique_allowed.items():
                            AllowedService.objects.update_or_create(
                                verified_user=user,
                                service_id=s_id,
                                defaults=s_meta
                            )
                            
                    logger.info(f"✅ Updated {len(new_perms)} capabilities for user {auth_user_id}")

                    # 3. Calculate Linked Capabilities (e.g. VETERINARY_DOCTOR)
                    cat_ids = [c["id"] for c in templates.get("categories", [])]
                    linked_caps = ProviderTemplateCategory.objects.filter(
                        super_admin_category_id__in=cat_ids
                    ).values_list("linked_capability", flat=True)
                    linked_caps = [lc for lc in linked_caps if lc]

                    if linked_caps:
                        # 🛡️ REPLACE permissions to remove old ones
                        updated_perms = list(set(linked_caps))
                        
                        # ⚠️ CRITICAL FIX #2: CONDITIONAL VETERINARY_CORE ADDITION
                        # WARNING: NEVER add VETERINARY_CORE unconditionally!
                        # Previously: if linked_caps: → VETERINARY_CORE added for ANY service
                        # Now: Only add if VETERINARY_* capabilities exist
                        
                        # Defensive check: filter only VETERINARY_* capabilities
                        vet_capabilities = [cap for cap in updated_perms if cap.startswith("VETERINARY_")]
                        has_vet_capabilities = len(vet_capabilities) > 0
                        
                        # Detailed logging for transparency
                        logger.info(f"📋 Linked capabilities: {updated_perms}")
                        logger.info(f"🏥 Veterinary capabilities: {vet_capabilities}")
                        
                        if has_vet_capabilities:
                            if "VETERINARY_CORE" not in updated_perms:
                                updated_perms.append("VETERINARY_CORE")
                                logger.info(f"✅ Auto-added VETERINARY_CORE (vet capabilities detected: {vet_capabilities})")
                            else:
                                logger.info(f"ℹ️  VETERINARY_CORE already present")
                        else:
                            logger.info(f"⏭️  Skipping VETERINARY_CORE (no veterinary capabilities in plan)")
                            
                        user.permissions = updated_perms
                        user.save()
                        logger.info(f"✅ Final user capabilities: {updated_perms}")
                    else:
                        # No linked capabilities at all
                        logger.info(f"ℹ️  No linked capabilities found, user.permissions remains empty")
                    
                    # 4. SYNC SUBSCRIPTION
                    purchased_plan_info = data.get("purchased_plan", {})
                    if purchased_plan_info and plan_id:
                        from service_provider.models import ProviderSubscription
                        from django.utils.dateparse import parse_datetime
                        
                        start_date = parse_datetime(purchased_plan_info.get("start_date")) if purchased_plan_info.get("start_date") else timezone.now()
                        end_date = parse_datetime(purchased_plan_info.get("end_date")) if purchased_plan_info.get("end_date") else None
                        
                        ProviderSubscription.objects.update_or_create(
                            verified_user=user,
                            defaults={
                                "plan_id": plan_id,
                                "billing_cycle_id": purchased_plan_info.get("billing_cycle_id"),
                                "start_date": start_date,
                                "end_date": end_date,
                                "is_active": True
                            }
                        )
                        logger.info(f"✅ Synced Subscription for user {auth_user_id}")

                    # 5. DYNAMIC CAPABILITIES (NEW System)
                    # 5. DYNAMIC CAPABILITIES (NEW System)
                    # Support both "dynamic_capabilities" (new) and "capabilities" (legacy/migration)
                    dynamic_caps = data.get("dynamic_capabilities") or data.get("data", {}).get("dynamic_capabilities")
                    if not dynamic_caps:
                        dynamic_caps = data.get("capabilities") or data.get("data", {}).get("capabilities")
                    
                    logger.info(f"DEBUG: Capabilities Processing | Raw Count: {len(dynamic_caps) if dynamic_caps else 0}")

                    if dynamic_caps:
                        from service_provider.models import Capability, FeatureModule, ProviderCapability
                        
                        # Clear old dynamic capabilities
                        ProviderCapability.objects.filter(user=user).delete()
                        
                        for cap_data in dynamic_caps:
                            # Handle simple string list ["DayCare", "Grooming"]
                            if isinstance(cap_data, str):
                                cap_key = cap_data
                                modules_list = []
                            else:
                                cap_key = cap_data.get("capability_key")
                                modules_list = cap_data.get("modules", [])

                            if not cap_key:
                                continue
                            
                            # Ensure Capability exists
                            capability_obj, _ = Capability.objects.get_or_create(
                                key=cap_key,
                                defaults={
                                    "label": cap_key.replace("_", " ").title(),
                                    "group": "Generated"
                                }
                            )
                            
                            # Assign to User
                            ProviderCapability.objects.create(
                                user=user,
                                capability=capability_obj,
                                is_active=True
                            )
                            
                            # Sync Modules
                            for mod_data in modules_list:
                                FeatureModule.objects.update_or_create(
                                    key=mod_data["key"],
                                    defaults={
                                        "capability": capability_obj,
                                        "name": mod_data["name"],
                                        "route": mod_data["route"],
                                        "icon": mod_data.get("icon", "tabler-box"),
                                        "sequence": mod_data.get("sequence", 0),
                                        "is_active": True
                                    }
                                )
                        logger.info(f"✅ Synced {len(dynamic_caps)} Dynamic Capabilities for user {auth_user_id}")

                except VerifiedUser.DoesNotExist:
                    logger.warning(f"⚠️ User {auth_user_id} not found for permission update")
                except Exception as e:
                    logger.error(f"❌ Error updating permissions for {auth_user_id}: {e}")
                
                # Publish Sync Event
                # Publish Sync Event
                try:
                    # Enrich payload with Technical Keys (from Templates)
                    service_lookup = {s["id"]: s for s in templates.get("services", [])}
                    category_lookup = {c["id"]: c for c in templates.get("categories", [])}
                    
                    final_sync_payload = []
                    
                    for p in perms_map.values():
                        s_id = p["service_id"]
                        c_id = p["category_id"]
                        
                        s_meta = service_lookup.get(s_id, {})
                        c_meta = category_lookup.get(c_id, {}) if c_id else {}
                        
                        payload_item = {
                            **p,
                            "service_key": s_meta.get("name"),       # e.g. VETERINARY_CORE
                            "service_name": s_meta.get("display_name"),
                            "category_key": c_meta.get("name"),      # e.g. Doctor Consultation
                            "linked_capability": c_meta.get("linked_capability"), # e.g. VETERINARY_DOCTOR
                        }
                        final_sync_payload.append(payload_item)
                        
                    logger.info(f"📤 Publishing Permissions Sync: {len(final_sync_payload)} items enriched")

                    from service_provider.kafka_producer import publish_permissions_synced
                    publish_permissions_synced(auth_user_id, final_sync_payload)
                except Exception as e:
                    logger.error(f"❌ Failed to publish sync event: {e}")

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


        else:
            logger.warning(f"⚠️ Unknown event type '{event_type}' received.")

    except Exception as e:
        logger.exception(f"❌ Error processing Kafka message: {e}")
