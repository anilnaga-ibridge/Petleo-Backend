import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory, ProviderTemplateService, ProviderCapabilityAccess
from service_provider.models import OrganizationEmployee, VerifiedUser, ServiceProvider
import uuid

def fix_patients():
    # 1. Get the Veterinary Management Service Template
    # super_admin_service_id derived from previous research
    VET_SERVICE_ID = '58409ace-6cd4-468d-a6d9-616792cbbd2e'
    try:
        vet_service = ProviderTemplateService.objects.get(super_admin_service_id=VET_SERVICE_ID)
        print(f"Found Veterinary Service Template: {vet_service.display_name}")
    except ProviderTemplateService.DoesNotExist:
        print("Error: Veterinary Service Template not found!")
        return

    # 2. Create the Patients Template Category if missing
    patients_cat, created = ProviderTemplateCategory.objects.get_or_create(
        name='Patients',
        service_id=vet_service.id,
        defaults={
            'super_admin_category_id': str(uuid.uuid4()),
            'linked_capability': 'VETERINARY_PATIENTS',
            'display_name': 'Patients'
        }
    )
    if created:
        print(f"Created Patients Template Category: {patients_cat.super_admin_category_id}")
    else:
        # Update it just in case it was half-configured
        patients_cat.linked_capability = 'VETERINARY_PATIENTS'
        patients_cat.save()
        print(f"Updated existing Patients Template Category: {patients_cat.super_admin_category_id}")

    # 3. Grant Organization Owner Access
    # Praveen's org owner is dhatha@gmail.com
    OWNER_EMAIL = 'dhatha@gmail.com'
    try:
        owner = VerifiedUser.objects.get(email=OWNER_EMAIL)
        
        # Check if they already have access
        access, access_created = ProviderCapabilityAccess.objects.get_or_create(
            user=owner,
            service_id=VET_SERVICE_ID,
            category_id=str(patients_cat.super_admin_category_id),
            defaults={
                'can_view': True,
                'can_create': True,
                'can_edit': True,
                'can_delete': True,
                'plan_id': 'SYSTEM_FIX'
            }
        )
        
        if access_created:
            print(f"Granted Patients access to Org Owner: {OWNER_EMAIL}")
        else:
            print(f"Org Owner {OWNER_EMAIL} already had access to Patients category.")

        # 4. Invalidate Cache for Praveen and other employees
        employees = OrganizationEmployee.objects.filter(organization__verified_user=owner)
        for emp in employees:
            emp.invalidate_permission_cache()
            print(f"Invalidated permission cache for employee: {emp.full_name}")

    except VerifiedUser.DoesNotExist:
        print(f"Error: Org Owner {OWNER_EMAIL} not found!")

if __name__ == "__main__":
    fix_patients()
