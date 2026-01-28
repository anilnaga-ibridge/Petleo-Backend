
import os
import django
import sys

# Setup Django
sys.path.append("/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, AllowedService
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService

user = VerifiedUser.objects.filter(auth_user_id="076875b0-ca6b-4d96-a5a5-36f29e8cd976").first()
if not user:
    print("User not found")
    sys.exit(1)

print(f"Checking services for: {user.full_name}")

# Check AllowedService
print("\n--- AllowedService ---")
allowed = AllowedService.objects.filter(verified_user=user)
for a in allowed:
    print(f"Use: {a.name} (ID: {a.id})")

# Check ProviderCapabilityAccess (Services)
print("\n--- ProviderCapabilityAccess (Direct Services) ---")
caps = ProviderCapabilityAccess.objects.filter(user=user, category_id__isnull=True)
for c in caps:
    # Try to find template name
    tmpl = ProviderTemplateService.objects.filter(super_admin_service_id=c.service_id).first()
    name = tmpl.name if tmpl else "Unknown"
    display = tmpl.display_name if tmpl else "Unknown"
    print(f"Service ID: {c.service_id} | Name: {name} | Display: {display}")
