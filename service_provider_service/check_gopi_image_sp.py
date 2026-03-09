
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import Organization, ServiceProviderProfile

auth_id = "87b9cb5d-ee9e-4e20-bf22-646b30b793ed"

print(f"--- Checking Service Provider Service for {auth_id} ---")
# Check Organization first
org = Organization.objects.filter(auth_user_id=auth_id).first()
if org:
    print(f"Organization found: {org.name}, Image: {org.image}")
else:
    print("Organization not found.")

# Check ServiceProviderProfile
profile = ServiceProviderProfile.objects.filter(auth_user_id=auth_id).first()
if profile:
    print(f"ServiceProviderProfile found: Image URL: {profile.image_url}")
else:
    print("ServiceProviderProfile not found.")
