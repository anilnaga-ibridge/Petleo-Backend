import os
import django
import uuid
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, OrganizationEmployee, ProviderRole, ProviderRoleCapability, EmployeeAvailability
from provider_dynamic_fields.models import ProviderTemplateFacility

def seed():
    # 1. Get the Organization
    org = ServiceProvider.objects.filter(provider_type='ORGANIZATION').first()
    if not org:
        print("No organization found")
        return
    
    print(f"Using Org: {org.id}")

    # 2. Create/Get a "Doctor" Role
    role, _ = ProviderRole.objects.get_or_create(
        provider=org,
        name="Senior Doctor",
        defaults={"description": "Can perform surgeries and consultations"}
    )
    
    # Add VETERINARY_DOCTOR capability to this role
    ProviderRoleCapability.objects.get_or_create(
        provider_role=role,
        capability_key="VETERINARY_DOCTOR"
    )
    print(f"Role 'Senior Doctor' ready with VETERINARY_DOCTOR capability")

    # 3. Assign this role to our ACTIVE employee
    # Emp: 709c36e6-69fc-4c58-b639-42f7bea302a5
    emp = OrganizationEmployee.objects.filter(auth_user_id='709c36e6-69fc-4c58-b639-42f7bea302a5').first()
    if emp:
        emp.provider_role = role
        emp.status = 'ACTIVE'
        emp.save()
        print(f"Assigned 'Senior Doctor' role to employee {emp.full_name}")
        
        # 4. Set Availability for the employee (e.g., Every day 09:00 - 18:00)
        for i in range(7):
            EmployeeAvailability.objects.update_or_create(
                employee=emp,
                day_of_week=i,
                defaults={
                    "start_time": time(9, 0),
                    "end_time": time(18, 0),
                    "slot_duration_minutes": 30,
                    "is_active": True
                }
            )
        print("Employee availability set for the whole week")

    # 5. Set required_capability for a facility
    # Let's find a 'Consultation' or similar facility
    facility = ProviderTemplateFacility.objects.filter(name__icontains='Consultation').first()
    if not facility:
        facility = ProviderTemplateFacility.objects.first()
    
    if facility:
        facility.required_capability = 'VETERINARY_DOCTOR'
        facility.save()
        print(f"Facility '{facility.name}' now requires 'VETERINARY_DOCTOR'")
        print(f"Test Facility ID: {facility.id}")

if __name__ == "__main__":
    seed()
