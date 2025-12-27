import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService

def debug_templates():
    print("--- Debugging Provider Template Services ---")
    services = ProviderTemplateService.objects.all()
    print(f"Total Services: {services.count()}")
    
    for s in services:
        print(f" - {s.display_name} ({s.super_admin_service_id})")
        
    # Check specifically for the IDs found in AllowedService
    # IDs from previous debug:
    # Grooming: 711fac84-16dc-4252-b7e3-6afb7ee57c71
    # Day Care: 2170653c-9de5-4f61-b1ca-35b1a0439b17
    # Training: d0de4652-d2e7-4cab-ae09-05999f365eed
    
    target_ids = [
        "711fac84-16dc-4252-b7e3-6afb7ee57c71",
        "2170653c-9de5-4f61-b1ca-35b1a0439b17",
        "d0de4652-d2e7-4cab-ae09-05999f365eed"
    ]
    
    print("\n--- Verifying Target IDs ---")
    for tid in target_ids:
        exists = ProviderTemplateService.objects.filter(super_admin_service_id=tid).exists()
        print(f"ID {tid}: {'✅ Found' if exists else '❌ MISSING'}")

if __name__ == "__main__":
    debug_templates()
