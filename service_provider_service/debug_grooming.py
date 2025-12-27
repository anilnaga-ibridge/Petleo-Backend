import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateService, 
    ProviderTemplateCategory
)

def debug_grooming():
    print("--- Debugging Grooming Service ---")
    
    user = VerifiedUser.objects.filter(email='ram@gmail.com').first()
    if not user:
        print("User not found")
        return

    # 1. Get Template IDs
    grooming_svc = ProviderTemplateService.objects.filter(display_name__icontains="Grooming").first()
    if not grooming_svc:
        print("Grooming Template NOT FOUND")
        return
        
    s_id_tmpl = grooming_svc.super_admin_service_id
    print(f"Template Service ID: '{s_id_tmpl}' (Type: {type(s_id_tmpl)})")
    
    # 2. Get Permissions
    perms = ProviderCapabilityAccess.objects.filter(user=user, service_id=s_id_tmpl)
    print(f"Found {perms.count()} permissions for this service ID.")
    
    for p in perms:
        print(f" - Perm Service ID: '{p.service_id}' (Type: {type(p.service_id)})")
        print(f"   Category ID: '{p.category_id}'")
        print(f"   Facility ID: '{p.facility_id}'")
        print(f"   Can View: {p.can_view}")
        
        if p.category_id:
            # Check if category exists
            cat = ProviderTemplateCategory.objects.filter(super_admin_category_id=p.category_id).first()
            if cat:
                print(f"   -> Linked to Category: {cat.name}")
            else:
                print(f"   -> ORPHANED CATEGORY ID")

    # 3. Fix: Ensure Root Permission exists for ALL services found in permissions
    print("\n--- Applying Global Fix ---")
    
    # Get all unique service IDs from existing permissions
    all_perms = ProviderCapabilityAccess.objects.filter(user=user)
    service_ids = set(p.service_id for p in all_perms if p.service_id)
    
    print(f"Found {len(service_ids)} unique services in permissions.")
    
    for s_id in service_ids:
        # Check if template exists
        tmpl = ProviderTemplateService.objects.filter(super_admin_service_id=s_id).first()
        name = tmpl.display_name if tmpl else "Unknown"
        
        root_perm, created = ProviderCapabilityAccess.objects.get_or_create(
            user=user,
            service_id=s_id,
            category_id=None,
            facility_id=None,
            defaults={'can_view': True, 'plan_id': 'FIX_ROOT_PERMS'}
        )
        if created:
            print(f"Created ROOT permission for Service: {name}")
        else:
            print(f"Root permission already exists for Service: {name}")
            if not root_perm.can_view:
                root_perm.can_view = True
                root_perm.save()
                print(f" -> Updated to can_view=True")

if __name__ == "__main__":
    debug_grooming()
