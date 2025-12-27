import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser, OrganizationEmployee, ServiceProvider, AllowedService
from provider_dynamic_fields.models import ProviderCapabilityAccess, ProviderTemplateService, ProviderTemplateCategory, ProviderTemplatePricing
from service_provider.views import EmployeeAssignmentViewSet

def test_granular_assignment():
    print("--- Testing Granular Employee Assignment ---")
    
    # 1. Setup User and Employee
    # Find an Org User
    try:
        # Assuming we have a provider with capabilities
        org_user = VerifiedUser.objects.filter(capabilities__isnull=False).distinct().first()
        if not org_user:
            print("No Org User with capabilities found. Skipping.")
            return

        provider = ServiceProvider.objects.get(verified_user=org_user)
        
        # Find or Create Employee
        employee = OrganizationEmployee.objects.filter(organization=provider).first()
        if not employee:
            print("No employee found for this provider.")
            return
            
        try:
            emp_user = VerifiedUser.objects.get(auth_user_id=employee.auth_user_id)
        except VerifiedUser.DoesNotExist:
            print("Creating dummy VerifiedUser for employee...")
            emp_user = VerifiedUser.objects.create(
                auth_user_id=employee.auth_user_id,
                email=employee.email or "test_emp@example.com",
                full_name=employee.full_name or "Test Employee",
                role="employee"
            )
        
        print(f"Org User: {org_user.email}")
        print(f"Employee: {emp_user.email} (ID: {employee.id})")
        
    except Exception as e:
        print(f"Setup failed: {e}")
        return

    factory = APIRequestFactory()
    view = EmployeeAssignmentViewSet()

    # 2. Test 'available' (GET)
    print("\n[TEST] Available Services (Tree)")
    request = factory.get('/api/provider/employee-assignments/available/')
    force_authenticate(request, user=org_user)
    request.user = org_user  # Manually set user for direct view call
    view.request = request
    view.format_kwarg = None
    
    response = view.available(request)
    if response.status_code == 200:
        data = response.data
        print(f"Received {len(data)} top-level services")
        if len(data) > 0:
            svc = data[0]
            print(f"Sample Service: {svc['service_name']}")
            print(f" - Categories: {len(svc['categories'])}")
            if len(svc['categories']) > 0:
                cat = svc['categories'][0]
                print(f"   - Sample Category: {cat['name']}")
                print(f"   - Facilities: {len(cat['facilities'])}")
    else:
        print(f"Failed: {response.status_code} - {response.data}")

    # Create Dummy Pricing for Test
    if len(data) > 0:
        svc = data[0]
        if len(svc['categories']) > 0:
            cat = svc['categories'][0]
            if cat['name'] == "Unknown Category":
                print("Skipping Unknown Category...")
            # Check if pricing exists, else create
            elif not ProviderTemplatePricing.objects.filter(category__super_admin_category_id=cat['id']).exists():
                print("Creating dummy pricing...")
                s_obj = ProviderTemplateService.objects.get(super_admin_service_id=svc['service_id'])
                c_obj = ProviderTemplateCategory.objects.get(super_admin_category_id=cat['id'])
                ProviderTemplatePricing.objects.create(
                    super_admin_pricing_id="test-pricing-1",
                    service=s_obj,
                    category=c_obj,
                    price=10.00,
                    duration="per_hour",
                    description="Test Pricing"
                )

    # 3. Test 'assign' (POST)
    print("\n[TEST] Assign Permissions")
    
    # Construct a payload based on available data
    payload_perms = []
    if len(data) > 0:
        svc = data[0]
        # Assign Service View
        payload_perms.append({"service_id": svc['service_id'], "can_view": True})
        
        if len(svc['categories']) > 0:
            cat = svc['categories'][0]
            # Assign Category View
            payload_perms.append({
                "service_id": svc['service_id'], 
                "category_id": cat['id'], 
                "can_view": True
            })
            
            # Assign Pricing View (if exists)
            # We need to re-fetch available to see the new pricing
            # But for now, let's just manually add the ID we created or found
            pricing_id = "test-pricing-1"
            payload_perms.append({
                "service_id": svc['service_id'], 
                "category_id": cat['id'], 
                "pricing_id": pricing_id,
                "can_view": True
            })
            
            if len(cat['facilities']) > 0:
                fac = cat['facilities'][0]
                # Assign Facility View
                payload_perms.append({
                    "service_id": svc['service_id'], 
                    "category_id": cat['id'], 
                    "facility_id": fac['id'],
                    "can_view": True
                })
    
    print(f"Assigning {len(payload_perms)} permissions...")
    
    request = factory.post(
        f'/api/provider/employee-assignments/{employee.id}/assign/',
        {"permissions": payload_perms},
        format='json'
    )
    force_authenticate(request, user=org_user)
    request.user = org_user
    request.data = {"permissions": payload_perms} # Manually set data
    view.request = request
    
    response = view.assign(request, pk=employee.id)
    print(f"Response: {response.status_code} - {response.data}")
    
    # 4. Verify Persistence
    print("\n[TEST] Verify Persistence")
    caps = ProviderCapabilityAccess.objects.filter(user=emp_user)
    print(f"ProviderCapabilityAccess count: {caps.count()}")
    for cap in caps:
        print(f" - S:{cap.service_id} C:{cap.category_id} F:{cap.facility_id} P:{cap.pricing_id} View:{cap.can_view}")
        
    allowed = AllowedService.objects.filter(verified_user=emp_user)
    print(f"AllowedService count: {allowed.count()}")

    # 5. Test 'assigned' (GET)
    print("\n[TEST] Assigned Services (Tree)")
    request = factory.get(f'/api/provider/employee-assignments/{employee.id}/assigned/')
    force_authenticate(request, user=org_user)
    request.user = org_user
    view.request = request
    
    response = view.assigned(request, pk=employee.id)
    if response.status_code == 200:
        data = response.data
        print(f"Received {len(data)} assigned services")
        # Should match what we assigned
    else:
        print(f"Failed: {response.status_code}")

if __name__ == "__main__":
    test_granular_assignment()
