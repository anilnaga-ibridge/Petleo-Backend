
from django.core.management.base import BaseCommand
from django.utils import timezone
from plans_coupens.models import PurchasedPlan, Invoice
from plans_coupens.billing_service import InvoiceOrchestrator, SettlementService
from admin_core.models import ProviderBillingProfile
import uuid

class Command(BaseCommand):
    help = "Generates a real-time billing pulse by converting pending purchases into PAID invoices."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🎬 Starting Revenue Pulse Generation..."))
        
        purchases = PurchasedPlan.objects.all()
        if not purchases.exists():
            self.stdout.write(self.style.WARNING("No purchases found to pulse."))
            return

        activated_count = 0

        for purchase in purchases:
            auth_user_id = purchase.user.auth_user_id
            if not auth_user_id:
                self.stdout.write(self.style.WARNING(f"⏩ Skip: {purchase.user.email} has no auth_user_id."))
                continue

            # Ensure baseline user exists in verified_users
            from admin_core.models import VerifiedUser
            if not VerifiedUser.objects.filter(auth_user_id=auth_user_id).exists():
                self.stdout.write(self.style.WARNING(f"⏩ Skip: {purchase.user.email} not found in verified_users cache."))
                continue

            # 1. Ensure a billing profile exists for the snapshot
            profile, created = ProviderBillingProfile.objects.get_or_create(
                verified_user_id=auth_user_id,
                defaults={
                    "legal_name": f"{purchase.user.first_name or 'Provider'} Organization",
                    "billing_address": "123 Business Way, Bangalore, KA",
                    "billing_state": "Karnataka",
                    "billing_state_code": "KA",
                    "is_incomplete": False
                }
            )

            # 2. Skip if already has an invoice
            if hasattr(purchase, 'invoice'):
                self.stdout.write(f"⏩ Skip: {purchase.user.email} already pulsed.")
                continue

            # 3. Create Issued Invoice
            try:
                invoice = InvoiceOrchestrator.create_invoice(purchase, purchase.user, profile)
                
                # 4. Process as PAID
                payment_ref = f"pulse_{uuid.uuid4().hex[:8]}"
                SettlementService.process_payment_success(
                    invoice_id=invoice.id,
                    payment_ref=payment_ref,
                    gateway_payload={"source": "PULSE_GENERATOR", "timestamp": timezone.now().isoformat()}
                )
                
                self.stdout.write(self.style.SUCCESS(f"✅ Pulsed: {purchase.plan.title} for {purchase.user.email} (Amt: {invoice.total_amount})"))
                activated_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to pulse {purchase.user.email}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✨ Pulse Complete. {activated_count} transactions activated."))
