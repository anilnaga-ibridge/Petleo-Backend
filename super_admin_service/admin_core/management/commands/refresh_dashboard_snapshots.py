
import logging
from django.core.management.base import BaseCommand
from admin_core.analytics_service import compute_executive_metrics, compute_intelligence_suite, compute_revenue_trend

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Rebuild Luxury Command Center analytics snapshots"

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Rebuild all intelligence suites (Revenue + Rankings)',
        )

    def handle(self, *args, **options):
        logger.info("🎬 Initializing Luxury Command Center refresh...")
        
        # 1. Executive Suite (Always)
        summary = compute_executive_metrics()
        self.stdout.write(self.style.SUCCESS(f"✅ Executive Suite Refreshed: ₹{summary['today_revenue']} Today Revenue"))

        if options['full']:
            # 2. Revenue Trend
            compute_revenue_trend()
            self.stdout.write(self.style.SUCCESS("✅ Revenue Velocity trends refreshed"))

            # 3. Intelligence Suite
            compute_intelligence_suite()
            self.stdout.write(self.style.SUCCESS("✅ Intelligence Suite (Rankings) refreshed"))

        self.stdout.write(self.style.SUCCESS("✨ Command Center intelligence updated successfully."))
