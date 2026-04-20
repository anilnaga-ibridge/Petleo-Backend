import hmac
import hashlib
import time
import logging
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from .models import (
    BillingSequence, TaxConfiguration, Invoice, 
    BillingAuditLog, PurchasedPlan, ProviderPlanCapability,
    LegacyEntitlementRecovery, MigrationRecordSequence
)
from admin_core.models import ProviderBillingProfile

logger = logging.getLogger(__name__)

class AuditSafeSequenceGenerator:
    """
    Ensures unique, sequential, monotonic invoice numbering using select_for_update.
    Format: PL-YYYY-000001
    """
    @staticmethod
    def get_next_number():
        year = timezone.now().year
        with transaction.atomic():
            sequence, created = BillingSequence.objects.select_for_update().get_or_create(year=year)
            sequence.last_number += 1
            sequence.save()
            
            return f"PL-{year}-{sequence.last_number:06d}"


class TaxEngine:
    """
    Logic for state-aware GST calculation and snapshotting.
    """
    @staticmethod
    def get_tax_details(buyer_state_code, base_amount):
        seller_state_code = settings.SELLER_STATE_CODE
        
        # Get standard GST rate from DB
        tax_config = TaxConfiguration.objects.filter(key="GST_STANDARD", is_active=True).first()
        gst_rate = tax_config.rate if tax_config else Decimal("18.00")
        
        details = {
            "gst_rate": gst_rate,
            "cgst_rate": Decimal("0.00"),
            "sgst_rate": Decimal("0.00"),
            "igst_rate": Decimal("0.00"),
            "tax_mode": "INTER_STATE",
        }
        
        if buyer_state_code.upper() == seller_state_code.upper():
            details["tax_mode"] = "INTRA_STATE"
            details["cgst_rate"] = gst_rate / 2
            details["sgst_rate"] = gst_rate / 2
        else:
            details["igst_rate"] = gst_rate
            
        details["gst_amount"] = (base_amount * gst_rate / 100).quantize(Decimal("0.01"))
        return details


class InvoiceOrchestrator:
    """
    Handles immutable snapshotting and invoice issuance.
    """
    @staticmethod
    def create_invoice(purchased_plan, provider, billing_profile):
        """
        Snapshots all data into the Invoice model.
        """
        tax_details = TaxEngine.get_tax_details(
            billing_profile.billing_state_code, 
            purchased_plan.plan.price
        )
        
        invoice_number = AuditSafeSequenceGenerator.get_next_number()
        
        with transaction.atomic():
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                purchased_plan=purchased_plan,
                provider=provider,
                
                # Snapshot Buyer
                buyer_name=billing_profile.legal_name,
                buyer_address=billing_profile.billing_address,
                buyer_gstin=billing_profile.billing_gstin,
                buyer_state_code=billing_profile.billing_state_code,
                
                # Snapshot Seller
                seller_name=settings.SELLER_NAME,
                seller_address=settings.SELLER_ADDRESS,
                seller_gstin=settings.SELLER_GSTIN,
                seller_state_code=settings.SELLER_STATE_CODE,
                
                # Snapshot Tax
                tax_mode=tax_details["tax_mode"],
                gst_rate=tax_details["gst_rate"],
                cgst_rate=tax_details["cgst_rate"],
                sgst_rate=tax_details["sgst_rate"],
                igst_rate=tax_details["igst_rate"],
                
                # Financials
                base_price=purchased_plan.plan.price,
                discount_amount=Decimal("0.00"), # Handle coupons later
                taxable_amount=purchased_plan.plan.price,
                gst_amount=tax_details["gst_amount"],
                total_amount=purchased_plan.plan.price + tax_details["gst_amount"],
                
                currency=purchased_plan.plan.currency,
                status="ISSUED"
            )
            
            BillingAuditLog.objects.create(
                invoice=invoice,
                event_type="invoice.created",
                description=f"Invoice {invoice_number} created and issued."
            )
            
            return invoice


class MigrationRecordGenerator:
    """
    Ensures unique, sequential, monotonic numbering for Migration Records.
    Format: MR-YYYY-000001
    """
    @staticmethod
    def get_next_number():
        year = timezone.now().year
        with transaction.atomic():
            sequence, created = MigrationRecordSequence.objects.select_for_update().get_or_create(year=year)
            sequence.last_number += 1
            sequence.save()
            return f"MR-{year}-{sequence.last_number:06d}"


class EntitlementOrchestrator:
    """
    Decouples permission synchronization from financial invoices.
    Handles rate-limiting and audit-safe legacy reconciliation.
    """
    @staticmethod
    def trigger_sync(purchased_plan, reason="MANUAL_REFRESH"):
        """
        Synthesizes the payload and pushes to Kafka.
        Enforces 30s rate limit per user for manual refreshes.
        """
        user = purchased_plan.user
        last_sync = purchased_plan.metadata_json.get("last_entitlement_sync_at")
        
        # 1. Rate Limit Check (1 request / 30 seconds)
        if last_sync and reason == "MANUAL_REFRESH":
            last_dt = timezone.datetime.fromisoformat(last_sync)
            if (timezone.now() - last_dt).total_seconds() < 30:
                logger.warning(f"Rate limit triggered for user {user.id} sync refresh.")
                return False, "Rate limit active. Please wait 30 seconds."

        try:
            from .payload_builder import build_unified_payload
            from .kafka_producer import publish_permissions_updated
            
            auth_user_id = str(user.auth_user_id)
            
            # Re-verify and ensure capabilities are mapped in DB before sync
            # (Ensures sync is always up-to-date with template changes)
            from .models import PlanCapability
            caps = PlanCapability.objects.filter(plan=purchased_plan.plan)
            
            # Atomic update of local capabilities
            with transaction.atomic():
                ProviderPlanCapability.objects.filter(
                    user=user, 
                    plan=purchased_plan.plan
                ).delete()
                
                new_caps = [
                    ProviderPlanCapability(
                        user=user,
                        plan=purchased_plan.plan,
                        service=cap.service,
                        category=cap.category,
                        facility=cap.facility,
                        limits=cap.limits,
                        permissions=cap.permissions
                    ) for cap in caps
                ]
                ProviderPlanCapability.objects.bulk_create(new_caps)

            data_bundle = build_unified_payload(
                user=user,
                plan=purchased_plan.plan,
                purchased_plan_id=str(purchased_plan.id),
                auth_user_id=auth_user_id
            )
            
            purchased_plan_info = {
                "id": str(purchased_plan.id),
                "plan_id": str(purchased_plan.plan.id),
                "plan_title": purchased_plan.plan.title,
                "billing_cycle": purchased_plan.billing_cycle,
                "start_date": purchased_plan.start_date.isoformat(),
                "end_date": purchased_plan.end_date.isoformat() if purchased_plan.end_date else None,
            }

            publish_permissions_updated(
                auth_user_id=auth_user_id,
                purchase_id=str(purchased_plan.id),
                permissions_list=data_bundle["perms_payload"],
                purchased_plan=purchased_plan_info,
                templates=data_bundle["templates"],
                dynamic_capabilities=data_bundle["dynamic_capabilities"],
                entitlement_source=purchased_plan.entitlement_source,
                is_legacy_reconciled=purchased_plan.is_legacy_reconciled
            )
            
            # Update last sync timestamp
            purchased_plan.metadata_json["last_entitlement_sync_at"] = timezone.now().isoformat()
            purchased_plan.save(update_fields=["metadata_json"])
            
            logger.info(f"📤 [SYNC] Entitlement published via {reason} for user {auth_user_id}")
            return True, "Entitlement synchronized successfully."
        except Exception as e:
            logger.exception(f"❌ [SYNC ERROR] Failed during {reason}: {e}")
            return False, str(e)


class SettlementService:
    """
    HMAC verification and atomic plan activation.
    """
    @staticmethod
    def verify_webhook_signature(payload, signature, timestamp, nonce):
        """
        HMAC Signature Verification with replay window.
        """
        secret = settings.BILLING_WEBHOOK_SECRET
        
        # 1. Replay Window Check
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > settings.BILLING_REPLAY_WINDOW_SECONDS:
            logger.warning(f"Replay attack detected or clock drift: {timestamp}")
            return False
            
        # 2. Reconstruct Message
        message = f"{timestamp}.{nonce}.{payload}".encode()
        expected_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

    @staticmethod
    @transaction.atomic
    def process_payment_success(invoice_id, payment_ref, gateway_payload):
        """
        Atomic PAID -> ACTIVE -> Permissions transaction.
        Idempotent by checking invoice status.
        """
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        
        if invoice.status == "PAID":
            logger.info(f"Invoice {invoice.invoice_number} already paid. proceeding to guarantee sync parity.")
        else:
            # 1. Update Invoice (Financials)
            invoice.status = "PAID"
            invoice.payment_reference = payment_ref
            invoice.payment_payload_json = gateway_payload
            invoice.paid_at = timezone.now()
            invoice.save()
            
            # 2. Update Plan Status
            purchased_plan = invoice.purchased_plan
            purchased_plan.status = "ACTIVE"
            purchased_plan.is_active = True
            purchased_plan.save()
        
        # 3. Grant Permissions (ProviderPlanCapability)
        # Avoid circular import if any
        from .models import PlanCapability
        caps = PlanCapability.objects.filter(plan=purchased_plan.plan)
        
        # Clear existing if any (unlikely for new purchase)
        ProviderPlanCapability.objects.filter(
            user=invoice.provider, 
            plan=purchased_plan.plan
        ).delete()
        
        new_caps = []
        for cap in caps:
            new_caps.append(ProviderPlanCapability(
                user=invoice.provider,
                plan=purchased_plan.plan,
                service=cap.service,
                category=cap.category,
                facility=cap.facility,
                limits=cap.limits,
                permissions=cap.permissions
            ))
        ProviderPlanCapability.objects.bulk_create(new_caps)
        
        # 4. Trigger Orchestrator for sync (Decoupled)
        success, msg = EntitlementOrchestrator.trigger_sync(purchased_plan, reason="PAYMENT_SETTLEMENT")
        if success:
            logger.info(f"📤 Cross-service permission sync published for user {purchased_plan.user.auth_user_id}")
        else:
            logger.error(f"❌ Kafka Sync Failed during settlement: {msg}")

        # 5. Audit Log
        BillingAuditLog.objects.create(
            invoice=invoice,
            event_type="payment.verified",
            description="Payment verified and permissions granted atomically.",
            payload={"payment_ref": payment_ref}
        )
        
        logger.info(f"Settlement complete for Invoice {invoice.invoice_number}")
        return True
