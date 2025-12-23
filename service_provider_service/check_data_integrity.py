import os
import django
import sys

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService

def check_integrity():
    # The user ID from the logs
    target_auth_id = "c87e1284-5597-4378-bad3-ec016ffe9651"
    
    print(f"--- Checking Data for User {target_auth_id} ---")
    
    try:
        user = VerifiedUser.objects.get(auth_user_id=target_auth_id)
        print(f"✅ User found: {user.email} (ID: {user.auth_user_id})")
    except VerifiedUser.DoesNotExist:
        print("❌ User NOT found!")
        return

    # Check Capabilities
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    print(f"Found {caps.count()} capabilities.")
    
    service_ids_in_caps = set()
    for cap in caps:
        print(f"  - Cap: Plan={cap.plan_id}, Service={cap.service_id}, Cat={cap.category_id}")
        if cap.service_id:
            service_ids_in_caps.add(cap.service_id)
            
    print(f"Unique Service IDs in Caps: {service_ids_in_caps}")

    # Check Templates
    print("\n--- Checking Templates ---")
    templates = ProviderTemplateService.objects.all()
    print(f"Total Template Services: {templates.count()}")
    
    for t in templates:
        print(f"  - Template: ID={t.super_admin_service_id}, Name={t.name}")
        
    # Check Match
    print("\n--- Checking Match ---")
    matched = ProviderTemplateService.objects.filter(super_admin_service_id__in=service_ids_in_caps)
    print(f"Matching Templates found via filter: {matched.count()}")
    
    for m in matched:
        print(f"  - Matched: {m.name}")

if __name__ == "__main__":
    check_integrity()
