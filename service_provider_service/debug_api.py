
import os
import sys
import django
from rest_framework.test import APIRequestFactory, force_authenticate
from service_provider.models import VerifiedUser

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider.settings")
django.setup()

from provider_dynamic_fields.views import ProviderFacilityViewSet
from provider_dynamic_fields.models import ProviderCategory

def test_api():
    print("Testing API View...")
    factory = APIRequestFactory()
    
    # 1. Find the Provider User (Use filtering to safely get one)
    # We need a user who owns the "Bathing" category we found earlier
    try:
        cat = ProviderCategory.objects.get(id="d30132e9-447b-4c9f-aaa5-b140a5a6929c")
        user = cat.provider
        print(f"User: {user.email}")
        
        # 2. Create Request
        # GET /api/provider/facilities/?category=...
        url = f"/api/provider/facilities/?category={cat.id}"
        request = factory.get(url)
        force_authenticate(request, user=user)
        
        # 3. Call View
        view = ProviderFacilityViewSet.as_view({'get': 'list'})
        response = view(request)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {response.data}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ids = [
        "d30132e9-447b-4c9f-aaa5-b140a5a6929c", # Bathing
        "895dd446-663f-4c36-a357-eb4033a26efe"  # Hair Cutting
    ]
    # for cat_id in ids:
    #     print(f"\n--- Checking Category {cat_id} ---")
    #     try:
    #         cat = ProviderCategory.objects.get(id=cat_id)
    #         user = cat.provider
    #     except:
    #          print("Skipping, category not found")
    #          continue
    #          
    #     factory = APIRequestFactory()
    #     url = f"/api/provider/facilities/?category={cat_id}"
    #     request = factory.get(url)
    #     force_authenticate(request, user=user)
    #     
    #     view = ProviderFacilityViewSet.as_view({'get': 'list'})
    #     response = view(request)
    #     
    #     print(f"Response Status: {response.status_code}")
    #     data = response.data
    #     if isinstance(data, list):
    #         print(f"Found {len(data)} facilities:")
    #         for item in data:
    #             print(f" - {item.get('name')} (Is Template: {item.get('is_template')})")
    #     else:
    #          print(f"Response Data: {data}")
    pass # To avoid syntax error from empty if block or similar but here it replaces the loop outright.

def test_pricing(): 
    print("\n--- Checking Pricing Endpoint ---")
    try:
        from provider_dynamic_fields.views import ProviderPricingViewSet
        # Use user with active plan
        email = "auto_8ce972f3-0c34-4868-86ad-0a4bb832ebd4@central-auth.local"
        user = VerifiedUser.objects.filter(email=email).first()
        if not user:
            print(f"User {email} not found! Trying to find ANY user with pricing...")
            # Fallback
            from provider_dynamic_fields.models import ProviderPricing
            p = ProviderPricing.objects.first()
            if p:
                user = p.provider
                print(f"Found user via pricing: {user.email}")
            else:
                 print("No pricing found for ANY user.")
                 return

        print(f"Checking for User: {user.email}")
        
        factory = APIRequestFactory()
        # List all rules
        url = "/api/provider/pricing/"
        request = factory.get(url)
        force_authenticate(request, user=user)
        
        view = ProviderPricingViewSet.as_view({'get': 'list'})
        response = view(request)
        
        print(f"Pricing Status: {response.status_code}")
        data = response.data
        if isinstance(data, list):
            print(f"Found {len(data)} total pricing rules (All Services):")
            for item in data:
                cat_id = item.get('category_id')
                fac_name = item.get('facility_name')
                svc_id = item.get('service_id')
                print(f" - Facility: {fac_name}, Cat ID: {cat_id}, Svc ID: {svc_id}")
                
            # Now specifically check for the expected service
            # We don't have cat anymore, so infer service from pricing rule if possible
            srv_id = None
            if data:
                srv_id = data[0].get('service_id')
                print(f"\nExample Service ID from results: {srv_id}")
            
            if srv_id:
                matches = [d for d in data if str(d.get('service_id')) == str(srv_id)]
                print(f"Found {len(matches)} matching service rules.")
        
        # Count DB directly
        from provider_dynamic_fields.models import ProviderPricing
        pricing_qs = ProviderPricing.objects.filter(provider=user)
        direct_count = pricing_qs.count()
        print(f"\nDirect DB Count for user {user.email}: {direct_count}")
        for p in pricing_qs:
             print(f" - ID: {p.id}, Active: {p.is_active}, Svc: {p.service_id}, Cat: {p.category_id}")
        
    except Exception as e:
        print(f"Error checking pricing: {e}")

if __name__ == "__main__":
    test_pricing()
