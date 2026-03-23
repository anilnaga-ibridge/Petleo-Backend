import os
import django
import sys

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import OrganizationEmployee, ProviderRole
from django.core.cache import cache

def fix_nurse():
    # 1. Target the nurse
    nurse = OrganizationEmployee.objects.filter(full_name='Veterinary Nurse').first()
    if not nurse:
        print("❌ 'Veterinary Nurse' not found.")
        return

    # 2. Find the Nurse role for this organization
    nurse_role = ProviderRole.objects.filter(provider=nurse.organization, name__iexact='Nurse').first()
    if not nurse_role:
        print("❌ 'Nurse' ProviderRole not found for this organization.")
        # Try to find any Nurse role
        nurse_role = ProviderRole.objects.filter(name__iexact='Nurse').first()
        if not nurse_role:
             print("❌ No 'Nurse' role found globally either.")
             return
        print(f"⚠️ Found 'Nurse' role in different org, using it (ID: {nurse_role.id})")

    # 3. Assign and Save
    print(f"Current role: {nurse.role}, ProviderRole: {nurse.provider_role}")
    nurse.provider_role = nurse_role
    nurse.role = 'Nurse' # Sync the string role too
    nurse.save()
    
    # 4. Invalidate Cache
    nurse.invalidate_permission_cache()
    print(f"✅ Successfully linked 'Veterinary Nurse' to ProviderRole '{nurse_role.name}'")
    print(f"✅ Cache invalidated for versions 0 and {nurse_role.version}")

if __name__ == "__main__":
    fix_nurse()
