from django.core.management.base import BaseCommand
from django.utils import timezone
from plans_coupens.models import PurchasedPlan, ProviderPlanPermission
from plans_coupens.kafka_producer import publish_permissions_revoked
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Check for expired plans and revoke permissions"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired_plans = PurchasedPlan.objects.filter(is_active=True, end_date__lt=now)

        if not expired_plans.exists():
            self.stdout.write(self.style.SUCCESS("No expired plans found."))
            return

        for plan in expired_plans:
            try:
                # 1. Deactivate Plan
                plan.is_active = False
                plan.save(update_fields=["is_active"])

                # 2. Remove Permissions
                deleted_count, _ = ProviderPlanPermission.objects.filter(
                    user=plan.user, 
                    plan=plan.plan
                ).delete()

                # 3. Publish Kafka Event
                publish_permissions_revoked(
                    auth_user_id=str(plan.user.id),
                    purchase_id=str(plan.id)
                )

                logger.info(f"✅ Plan expired for user {plan.user.email}. Revoked {deleted_count} permissions.")
                self.stdout.write(self.style.SUCCESS(f"Expired plan {plan.id} for user {plan.user.id}"))

            except Exception as e:
                logger.error(f"❌ Error expiring plan {plan.id}: {e}")
                self.stdout.write(self.style.ERROR(f"Failed to expire plan {plan.id}: {e}"))
