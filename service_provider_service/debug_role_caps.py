import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ProviderRole

# Check Veterinary Doctor role capabilities
roles = ProviderRole.objects.filter(name__icontains='doctor')
for role in roles:
    caps = role.capabilities.all()
    print(f"\nRole: {role.name}")
    for cap in caps:
        print(f"  - {cap.capability_key}")
