import logging
from django.db import transaction
from .consumer_base import RobustKafkaConsumer
from .schemas import PermissionSyncPayload
from .mapper import PermissionMapper
from service_provider.models import VerifiedUser

logger = logging.getLogger(__name__)

class PermissionSyncConsumer(RobustKafkaConsumer):
    """
    Subclass that implements domain-specific logic for permission sync.
    Handles Template Sync, Capability Sync, and Dynamic Module Sync.
    """
    
    def validate_payload(self, payload: dict):
        """Strictly validates incoming Kafka message."""
        return PermissionSyncPayload.validate_and_parse(payload)

    def handle_event(self, parsed_payload: PermissionSyncPayload):
        """
        Processes a validated permission payload.
        Ensures atomic updates to permissions, allowed services, and dynamic capabilities.
        """
        provider_id = parsed_payload.provider_id
        
        try:
            user = VerifiedUser.objects.get(auth_user_id=provider_id)
        except VerifiedUser.DoesNotExist:
            logger.error(f"❌ User not found for permission sync: {provider_id}")
            raise Exception(f"User {provider_id} not found in Provider Service.")

        # Shared Template Models (Import here to avoid circularity)
        from provider_dynamic_fields.models import (
            ProviderCapabilityAccess,
            ProviderTemplateService,
            ProviderTemplateCategory,
            ProviderTemplateFacility
        )
        from service_provider.models import (
            AllowedService, Capability, ProviderCapability
        )

        with transaction.atomic():
            # 0. TEMPLATE METADATA SYNC (Shadow Templates for Sidebar/UI)
            templates = parsed_payload.templates
            if templates:
                logger.info(f"🏗️ Syncing templates for {user.email}")
                
                # A. Services
                for s_data in templates.get("services", []):
                    ProviderTemplateService.objects.update_or_create(
                        super_admin_service_id=str(s_data["id"]),
                        defaults={
                            "name": s_data["name"],
                            "display_name": s_data["display_name"],
                            "icon": s_data.get("icon", "tabler-box")
                        }
                    )
                
                # B. Categories
                for c_data in templates.get("categories", []):
                    svc_tmpl = ProviderTemplateService.objects.filter(super_admin_service_id=str(c_data["service_id"])).first()
                    if svc_tmpl:
                        ProviderTemplateCategory.objects.update_or_create(
                            super_admin_category_id=str(c_data["id"]),
                            defaults={
                                "service": svc_tmpl,
                                "name": c_data["name"],
                                "category_key": c_data.get("category_key", c_data["name"])
                            }
                        )
                
                # C. Facilities
                for f_data in templates.get("facilities", []):
                    cat_tmpl = ProviderTemplateCategory.objects.filter(super_admin_category_id=str(f_data.get("category_id"))).first()
                    if cat_tmpl:
                        ProviderTemplateFacility.objects.update_or_create(
                            super_admin_facility_id=str(f_data["id"]),
                            defaults={
                                "category": cat_tmpl,
                                "name": f_data["name"],
                                "description": f_data.get("description", "")
                            }
                        )

            # 1. PERMISSION CAPABILITIES SYNC
            ProviderCapabilityAccess.objects.filter(user=user).delete()
            
            cap_nodes = parsed_payload.capabilities
            logger.info(f"🔄 Syncing {len(cap_nodes)} capability nodes for {user.email}")

            for cap in cap_nodes:
                db_fields = PermissionMapper.map_to_db_fields(cap)
                ProviderCapabilityAccess.objects.create(
                    user=user,
                    plan_id=parsed_payload.plan_id,
                    service_id=cap.service_id,
                    category_id=cap.category_id,
                    facility_id=cap.facility_id,
                    pricing_id=cap.pricing_id,
                    **db_fields
                )

            # 2. ACTUAL PROVIDER MODELS SYNC (Auto-Seed Service Detail Views)
            # This ensures "Grooming -> Bathing" or "Boarding -> Basic Boarding" 
            # actually exists in the provider's data, not just the sidebar tree.
            from provider_dynamic_fields.models import ProviderCategory, ProviderFacility
            
            for cap in cap_nodes:
                if not cap.service_id or not cap.category_id:
                    continue
                
                # A. Sync Actual Category
                cat_tmpl = ProviderTemplateCategory.objects.filter(super_admin_category_id=cap.category_id).first()
                if cat_tmpl:
                    p_cat, _ = ProviderCategory.objects.update_or_create(
                        provider=user,
                        service_id=cap.service_id,
                        name=cat_tmpl.name,
                        defaults={
                            "description": cat_tmpl.description or f"Automated {cat_tmpl.name} from plan."
                        }
                    )
                    
                    # B. Sync Actual Facility (if present in cap)
                    if cap.facility_id:
                        fac_tmpl = ProviderTemplateFacility.objects.filter(super_admin_facility_id=cap.facility_id).first()
                        if fac_tmpl:
                            p_fac, _ = ProviderFacility.objects.update_or_create(
                                provider=user,
                                category=p_cat,
                                name=fac_tmpl.name,
                                defaults={
                                    "description": fac_tmpl.description,
                                    "price": fac_tmpl.base_price,
                                    "protocol_type": fac_tmpl.protocol_type,
                                    "duration_minutes": fac_tmpl.duration_minutes,
                                    "pricing_strategy": fac_tmpl.pricing_strategy,
                                    "base_price": fac_tmpl.base_price,
                                    "buffer_minutes": fac_tmpl.buffer_minutes,
                                    "slot_granularity": fac_tmpl.slot_granularity
                                }
                            )
                            
                            # C. Sync Actual Pricing Rule (Required for frontend to show item)
                            from provider_dynamic_fields.models import ProviderPricing
                            ProviderPricing.objects.update_or_create(
                                provider=user,
                                facility=p_fac,
                                defaults={
                                    "service_id": cap.service_id,
                                    "category_id": str(p_cat.id),
                                    "price": fac_tmpl.base_price,
                                    "billing_unit": "PER_SESSION",
                                    "duration_minutes": fac_tmpl.duration_minutes,
                                    "service_duration_type": "MINUTES" if fac_tmpl.protocol_type in ["MINUTES_BASED", "DAY_BASED"] else "SESSIONS",
                                    "pricing_model": fac_tmpl.pricing_strategy,
                                    "description": fac_tmpl.description,
                                    "is_active": True
                                }
                            )

            # 3. ALLOWED SERVICES SYNC (Flat discovery for Sidebar Modules)
            AllowedService.objects.filter(verified_user=user).delete()
            seen_services = set(c.service_id for c in cap_nodes if c.service_id)
            for s_id in seen_services:
                # Find the template for the correct display name/icon
                svc_tmpl = ProviderTemplateService.objects.filter(super_admin_service_id=s_id).first()
                name = svc_tmpl.display_name if svc_tmpl else s_id.replace("_", " ").title()
                icon = svc_tmpl.icon if svc_tmpl else "tabler-box"
                
                AllowedService.objects.update_or_create(
                    verified_user=user,
                    service_id=s_id,
                    defaults={"name": name, "icon": icon}
                )

            # 3. DYNAMIC CAPABILITIES (TECHNICAL KEYS)
            ProviderCapability.objects.filter(user=user).delete()
            for s_id in seen_services:
                cap_obj, _ = Capability.objects.get_or_create(
                    key=s_id.upper(),
                    defaults={"label": s_id.replace("_", " ").title()}
                )
                ProviderCapability.objects.create(
                    user=user, 
                    capability=cap_obj, 
                    is_active=True
                )

        logger.info(f"✅ Full Sync Completed for {user.email}")
