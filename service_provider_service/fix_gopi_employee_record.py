"""
Fix Script: Create OrganizationEmployee record for Gopi g in service_provider_service.

Gopi g is an ORGANIZATION provider but has no OrganizationEmployee record 
for himself. This means the AvailabilityService cannot find his schedules.

Run this script from the service_provider_service directory:
    python3 fix_gopi_employee_record.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, OrganizationEmployee

# Gopi g's known identifiers
GOPI_AUTH_USER_ID = '87b9cb5d-ee9e-4e20-bf22-646b30b793ed'
GOPI_SP_ID = '9c856d87-e98f-42fd-a474-dc71fc547537'

def fix_gopi_employee():
    print("🔍 Looking up Gopi's ServiceProvider record...")
    try:
        provider = ServiceProvider.objects.get(id=GOPI_SP_ID)
        print(f"✅ Found: {provider.verified_user.full_name} (type={provider.provider_type})")
    except ServiceProvider.DoesNotExist:
        print("❌ ServiceProvider not found. Aborting.")
        return

    print("\n🔍 Checking for existing OrganizationEmployee...")
    existing = OrganizationEmployee.objects.filter(
        auth_user_id=GOPI_AUTH_USER_ID,
        organization=provider
    ).first()

    if existing:
        print(f"ℹ️  OrganizationEmployee already exists: {existing.full_name} (status={existing.status})")
        return

    print("⚠️  No existing record found. Creating OrganizationEmployee for Gopi g...")
    emp = OrganizationEmployee.objects.create(
        auth_user_id=GOPI_AUTH_USER_ID,
        organization=provider,
        full_name='Gopi g',
        email=provider.verified_user.email if hasattr(provider.verified_user, 'email') else '',
        role='doctor',
        status='ACTIVE',
        specialization='General Veterinary',
        consultation_fee=0.00,
        average_rating=0.0,
        total_ratings=0,
        created_by=GOPI_AUTH_USER_ID,  # created by himself (self-registered org owner)
    )

    print(f"✅ Created OrganizationEmployee: {emp.full_name} | auth_user_id={emp.auth_user_id} | status={emp.status}")
    print("\n✅ Fix complete! Gopi g is now an active employee in his organization.")
    print("Next: Run fix_gopi_vet_assignment.py in veterinary_service to create StaffClinicAssignment.")

if __name__ == "__main__":
    fix_gopi_employee()
