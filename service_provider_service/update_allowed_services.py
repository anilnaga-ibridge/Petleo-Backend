
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import AllowedService

# Update all services named "Veterinary" or "VETERINARY" to "VETERINARY_CORE"
updated_count = AllowedService.objects.filter(name__iexact="Veterinary").update(name="VETERINARY_CORE")
print(f"Updated {updated_count} 'Veterinary' services to 'VETERINARY_CORE'.")

# Verify
for s in AllowedService.objects.filter(name="VETERINARY_CORE"):
    print(f"Verified: {s.name} - {s.verified_user}")
