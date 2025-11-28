from django.core.management.base import BaseCommand
import os
import django

class Command(BaseCommand):
    help = "Runs the dynamic fields Kafka consumer to sync definitions from SuperAdmin."

    def handle(self, *args, **options):
        # Import here to ensure Django settings are loaded
        from dynamic_fields.kafka_consumer import run_consumer
        self.stdout.write(self.style.SUCCESS("Starting dynamic fields consumer..."))
        run_consumer()
