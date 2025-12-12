import os
import django
import logging

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

# Configure logging to see the output
logging.basicConfig(level=logging.INFO)

from service_provider.kafka_producer import publish_document_uploaded

print("--- Starting Manual Service Provider Producer Test ---")
try:
    publish_document_uploaded("test_provider", "test_doc", "http://example.com", "test.pdf")
    print("--- Test Completed Successfully (Check logs for warning) ---")
except Exception as e:
    print(f"--- Test FAILED with Exception: {e} ---")
