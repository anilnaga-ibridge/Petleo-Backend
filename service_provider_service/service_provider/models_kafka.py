import uuid
from django.db import models
from django.utils import timezone

class KafkaProcessedEvent(models.Model):
    """
    Stores processed Kafka event IDs to ensure idempotent processing.
    """
    event_id = models.UUIDField(primary_key=True, help_text="Unique UUID from the Kafka message payload")
    topic = models.CharField(max_length=255)
    processed_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')], default='SUCCESS')
    error_details = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "kafka_processed_events"
        indexes = [
            models.Index(fields=['event_id', 'topic']),
        ]

    def __str__(self):
        return f"{self.event_id} ({self.status})"

class KafkaDeadLetterQueue(models.Model):
    """
    Stores failed Kafka messages for manual auditing and re-processing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_event_id = models.UUIDField(null=True, blank=True)
    topic = models.CharField(max_length=255)
    payload = models.JSONField()
    error_message = models.TextField()
    stack_trace = models.TextField(null=True, blank=True)
    failed_at = models.DateTimeField(default=timezone.now)
    retry_count = models.IntegerField(default=0)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "kafka_dead_letter_queue"
        ordering = ['-failed_at']

    def __str__(self):
        return f"DLQ: {self.original_event_id or self.id} ({self.topic})"
