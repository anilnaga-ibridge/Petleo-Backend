import os
import django
import sys

sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()
from provider_dynamic_fields.models import ProviderDocument

print(f"ServiceProvider Total Docs: {ProviderDocument.objects.count()}")
for doc in ProviderDocument.objects.all():
    print(f"  - Doc: {doc.filename}, Provider: {doc.verified_user.auth_user_id}")
