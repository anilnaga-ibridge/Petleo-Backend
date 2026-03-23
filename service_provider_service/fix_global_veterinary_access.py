import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory, ProviderCapabilityAccess
from service_provider.models import ServiceProvider

def standardize_access():
    # 1. Identify all Veterinary-related Services
    vet_svc_names = ["Veterinary", "Veterinary Management"]
    vet_svcs = ProviderTemplateService.objects.filter(display_name__in=vet_svc_names)
    vet_svc_ids = list(vet_svcs.values_list("super_admin_service_id", flat=True))
    
    print(f"Standardizing access for {len(vet_svc_ids)} Veterinary services: {vet_svc_ids}")

    # 2. Define Standard Categories that should always exist
    standard_categories = [
        {"name": "Patients", "cap": "VETERINARY_PATIENTS", "uuid": "VET_CAT_VETERINARY_PATIENTS"},
        {"name": "Schedule", "cap": "VETERINARY_SCHEDULE", "uuid": "VET_CAT_VETERINARY_SCHEDULE"},
        {"name": "Reception Desk", "cap": "VETERINARY_VISITS", "uuid": "VET_CAT_VETERINARY_VISITS"},
        {"name": "Nurse Station", "cap": "VETERINARY_VITALS", "uuid": "VET_CAT_VETERINARY_VITALS"},
        {"name": "Laboratory", "cap": "VETERINARY_LABS", "uuid": "VET_CAT_VETERINARY_LABS"},
        {"name": "veterinary_doctor", "cap": "VETERINARY_DOCTOR", "uuid": "VET_CAT_VETERINARY_DOCTOR"},
        {"name": "veterinary_pharmacy", "cap": "VETERINARY_PHARMACY", "uuid": "VET_CAT_VETERINARY_PHARMACY"},
        {"name": "Medicine Reminders", "cap": "VETERINARY_MEDICINE_REMINDERS", "uuid": "VET_CAT_VETERINARY_MEDICINE_REMINDERS"},
    ]

    # 3. For each Service Provider (Org)
    for provider in ServiceProvider.objects.all():
        owner = provider.verified_user
        
        # Check which vet service they are using
        active_vet_svc = ProviderCapabilityAccess.objects.filter(
            user=owner, 
            service_id__in=vet_svc_ids,
            category_id__isnull=True
        ).first()

        if active_vet_svc:
            print(f"\nProcessing Org: {provider.detailed_profile.clinic_name if hasattr(provider, 'detailed_profile') else provider.id} ({owner.email})")
            svc_id = active_vet_svc.service_id
            
            for cat_info in standard_categories:
                # Use a specific UUID for standard categories to avoid duplicates
                # or find existing one by name and linked cap
                # Identify Category cautiously (handle duplicates)
                cat_obj = ProviderTemplateCategory.objects.filter(
                    linked_capability=cat_info["cap"]
                ).first()
                
                if not cat_obj:
                    cat_obj = ProviderTemplateCategory.objects.filter(
                        name=cat_info["name"]
                    ).first()
                
                if not cat_obj:
                    cat_obj = ProviderTemplateCategory.objects.create(
                        name=cat_info["name"],
                        linked_capability=cat_info["cap"],
                        super_admin_category_id=cat_info["uuid"]
                    )
                
                # Link this category to the organization's service access
                access, access_created = ProviderCapabilityAccess.objects.get_or_create(
                    user=owner,
                    service_id=svc_id,
                    category_id=cat_obj.super_admin_category_id,
                    defaults={
                        "can_view": True,
                        "can_create": True,
                        "can_edit": True,
                        "can_delete": True
                    }
                )
                
                if access_created:
                    print(f"  ✅ Added access to {cat_info['name']}")

standardize_access()
