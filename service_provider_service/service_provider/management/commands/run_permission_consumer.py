from django.core.management.base import BaseCommand
import logging
from service_provider.kafka.permission_consumer import PermissionSyncConsumer

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Runs the Permission Synchronization Kafka consumer."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting Permission Sync Consumer..."))
        
        # Initialize the consumer with the correct group ID and topic
        consumer = PermissionSyncConsumer(
            group_id="permission_sync_group",
            topics=["provider.permissions.updated"]
        )
        
        try:
            consumer.listen()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopped by user."))
        except Exception as e:
            logger.exception(f"Fatal consumer error: {e}")
            self.stderr.write(self.style.ERROR(f"Fatal error: {e}"))
