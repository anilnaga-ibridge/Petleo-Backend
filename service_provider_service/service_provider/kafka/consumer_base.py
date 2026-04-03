import logging
import time
import traceback
from django.db import transaction, DatabaseError
from .schemas import ValidationError
from ..models_kafka import KafkaProcessedEvent, KafkaDeadLetterQueue

logger = logging.getLogger(__name__)

class RobustKafkaConsumer:
    """
    Enterprise-grade Kafka Consumer with idempotency, retry, and DLQ support.
    """
    
    def __init__(self, topic: str, max_retries: int = 3):
        self.topic = topic
        self.max_retries = max_retries

    def process(self, payload: dict):
        """Main entry point for processing a Kafka message."""
        event_id = payload.get("event_id")
        
        if not event_id:
            logger.error(f"❌ Missing event_id in payload for topic {self.topic}")
            self._move_to_dlq(payload, "Missing event_id")
            return

        # 1. Idempotency Check
        if KafkaProcessedEvent.objects.filter(event_id=event_id, topic=self.topic).exists():
            logger.info(f"⏭️ Skipping already processed event: {event_id}")
            return

        # 2. Schema Validation
        try:
            parsed_payload = self.validate_payload(payload)
        except ValidationError as e:
            logger.error(f"❌ Validation failed for event {event_id}: {str(e)}")
            self._move_to_dlq(payload, str(e))
            return

        # 3. Processing with Retries & Atomic Transaction
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                with transaction.atomic():
                    # Business logic implementation
                    self.handle_event(parsed_payload)
                    
                    # Log success (Idempotency)
                    KafkaProcessedEvent.objects.create(
                        event_id=event_id,
                        topic=self.topic,
                        status='SUCCESS'
                    )
                
                logger.info(f"✅ Successfully processed event: {event_id}")
                return # Exit on success
            except DatabaseError as e:
                retry_count += 1
                wait_time = 2 ** retry_count # Exponential backoff
                logger.warning(f"⚠️ Retry {retry_count}/{self.max_retries} for event {event_id}. Waiting {wait_time}s. Error: {str(e)}")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"❌ Fatal error processing event {event_id}: {str(e)}")
                self._move_to_dlq(payload, str(e), traceback.format_exc(), retry_count)
                return

        # If retries exhausted
        logger.error(f"🚨 Exhausted retries for event {event_id}")
        self._move_to_dlq(payload, "Exhausted retries", retry_count=retry_count)

    def validate_payload(self, payload: dict):
        """Override in subclasses to use specific schemas."""
        raise NotImplementedError

    def handle_event(self, parsed_payload):
        """Override in subclasses to implement domain logic."""
        raise NotImplementedError

    def _move_to_dlq(self, payload: dict, error_msg: str, stack_trace: str = None, retry_count: int = 0):
        """Safely stores failed messages for manual auditing."""
        try:
            KafkaDeadLetterQueue.objects.create(
                original_event_id=payload.get("event_id"),
                topic=self.topic,
                payload=payload,
                error_message=error_msg,
                stack_trace=stack_trace,
                retry_count=retry_count
            )
            logger.warning(f"📥 Moved event {payload.get('event_id')} to DLQ: {error_msg}")
        except Exception as dlq_err:
            logger.critical(f"🚨 FAILED TO MOVE TO DLQ: {dlq_err}. Original error: {error_msg}. Payload was: {payload}")
