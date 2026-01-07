import os
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole, ProviderRoleCapability, ServiceProvider

ROLE_TEMPLATES = {
    "Receptionist": ["VETERINARY_CORE", "VETERINARY_VISITS"],
    "Nurse": ["VETERINARY_CORE", "VETERINARY_VITALS", "VETERINARY_LABS"],
    "Doctor": ["VETERINARY_CORE", "VETERINARY_VISITS", "VETERINARY_VITALS", "VETERINARY_PRESCRIPTIONS", "VETERINARY_LABS"],
    "Lab Technician": ["VETERINARY_CORE", "VETERINARY_LABS"],
    "Pharmacy": ["VETERINARY_CORE", "VETERINARY_MEDICINE_REMINDERS"]
}

LEGACY_TO_NEW = {
    "receptionist": "Receptionist",
    "vitals staff": "Nurse",
    "doctor": "Doctor",
    "lab tech": "Lab Technician",
    "pharmacy": "Pharmacy"
}

def backfill_roles():
    print("--- Starting Role Backfill ---")
    employees = OrganizationEmployee.objects.filter(provider_role__isnull=True)
    print(f"Found {employees.count()} employees to backfill.")

    for emp in employees:
        legacy_role = (emp.role or "employee").lower()
        new_role_name = LEGACY_TO_NEW.get(legacy_role)
        
        if not new_role_name:
            print(f"Skipping employee {emp.auth_user_id} with unknown legacy role: {legacy_role}")
            continue

        # Get or create the role for this provider
        role, created = ProviderRole.objects.get_or_create(
            provider=emp.organization,
            name=new_role_name,
            defaults={"description": f"Standard {new_role_name} role"}
        )
        
        if created:
            print(f"Created role '{new_role_name}' for provider {emp.organization.id}")
            # Add capabilities
            for cap_key in ROLE_TEMPLATES[new_role_name]:
                ProviderRoleCapability.objects.get_or_create(
                    provider_role=role,
                    capability_key=cap_key
                )

        # Assign role to employee
        emp.provider_role = role
        emp.save()
        print(f"Assigned '{new_role_name}' to employee {emp.full_name or emp.auth_user_id}")

    print("--- Backfill Complete ---")

if __name__ == "__main__":
    backfill_roles()
