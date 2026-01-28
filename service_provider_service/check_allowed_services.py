
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import AllowedService

print(f"Total Allowed Services: {AllowedService.objects.count()}")
for s in AllowedService.objects.all():
    print(f"Service: {s.name} - User: {s.verified_user}")
