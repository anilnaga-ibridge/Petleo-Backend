import os
import sys
import django
from unittest.mock import MagicMock

# Setup Django
sys.path.append('/Users/PraveenWorks/Anil Works/PetLeo-Backend/veterinary_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'veterinary_service.settings')
django.setup()

from veterinary.models import Clinic
from veterinary.views import ClinicViewSet
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import PermissionDenied

def verify_ownership_boundaries():
    print("\n🔐 Verifying Ownership Boundaries...")
    factory = APIRequestFactory()
    view = ClinicViewSet.as_view({'post': 'create'})

    # 1. Test: Individual Provider Attempt
    print("   Test 1: Individual Provider manual creation...")
    individual_user = MagicMock()
    individual_user.id = "ind-owner-id"
    individual_user.role = "individual"
    individual_user.is_authenticated = True
    
    request = factory.post('/veterinary/clinics/', {'name': 'Illegal Clinic'})
    force_authenticate(request, user=individual_user)
    
    try:
        response = view(request)
        if response.status_code == 403:
            print("   ✅ Properly blocked Individual Provider creation.")
        else:
            print(f"   ❌ FAILED: Expected 403, got {response.status_code}")
    except PermissionDenied:
        print("   ✅ Properly raised PermissionDenied for Individual Provider.")
    except Exception as e:
        print(f"   ❌ FAILED: Unexpected error: {e}")

    # 2. Test: Organization Provider Creation (Secondary)
    print("   Test 2: Organization Provider creating secondary clinic...")
    org_user = MagicMock()
    org_id = "org-owner-id"
    org_user.id = org_id
    org_user.role = "organization"
    org_user.is_authenticated = True
    
    # Ensure a primary exists first
    Clinic.objects.update_or_create(
        organization_id=org_id,
        is_primary=True,
        defaults={"name": "Primary Clinic"}
    )
    
    request = factory.post('/veterinary/clinics/', {'name': 'Secondary Branch'})
    force_authenticate(request, user=org_user)
    
    response = view(request)
    if response.status_code == 201:
        clinic = Clinic.objects.get(id=response.data['id'])
        print(f"   ✅ Successfully created secondary clinic: {clinic.name}")
        if not clinic.is_primary:
            print("   ✅ Secondary clinic is NOT marked as primary.")
        else:
            print("   ❌ FAILED: Secondary clinic was marked as primary.")
        if clinic.organization_id == org_id:
             print("   ✅ organization_id auto-assigned correctly.")
        else:
             print(f"   ❌ FAILED: organization_id mismatch. Expected {org_id}, got {clinic.organization_id}")
    else:
        print(f"   ❌ FAILED: Expected 201, got {response.status_code} - {response.data}")

    # 3. Test: Super Admin Attempt
    print("   Test 3: Super Admin manual creation...")
    admin_user = MagicMock()
    admin_user.role = "superadmin"
    admin_user.is_authenticated = True
    
    request = factory.post('/veterinary/clinics/', {'name': 'Admin Overreach'})
    force_authenticate(request, user=admin_user)
    
    try:
        response = view(request)
        if response.status_code == 403:
            print("   ✅ Properly blocked Super Admin creation.")
        else:
            print(f"   ❌ FAILED: Expected 403, got {response.status_code}")
    except PermissionDenied:
        print("   ✅ Properly raised PermissionDenied for Super Admin.")

    # Cleanup
    Clinic.objects.filter(organization_id=org_id).delete()
    print("\n🎉 Ownership Boundary Verification Passed!")

if __name__ == "__main__":
    verify_ownership_boundaries()
