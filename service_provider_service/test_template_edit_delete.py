import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from service_provider.models import VerifiedUser
from provider_dynamic_fields.views import ProviderCategoryViewSet, ProviderFacilityViewSet
from provider_dynamic_fields.models import ProviderTemplateCategory, ProviderTemplateFacility, ProviderCategory, ProviderCapabilityAccess

def test_template_edit_delete():
    # 1. Get User
    try:
        user = VerifiedUser.objects.get(email="nagaanil29@gmail.com")
    except VerifiedUser.DoesNotExist:
        print("User not found")
        return

    factory = APIRequestFactory()

    # ==========================================
    # TEST 1: EDIT TEMPLATE CATEGORY (Shadowing)
    # ==========================================
    t_cat = ProviderTemplateCategory.objects.first()
    if t_cat:
        print(f"\n--- Testing Edit Template Category: {t_cat.name} ({t_cat.id}) ---")
        
        # Ensure permission exists first (so we can delete it)
        ProviderCapabilityAccess.objects.get_or_create(
            user=user,
            category_id=t_cat.super_admin_category_id,
            defaults={"plan_id": "test", "can_view": True}
        )
        
        view = ProviderCategoryViewSet.as_view({'put': 'update'})
        data = {"name": f"{t_cat.name} (Customized)", "service_id": t_cat.service.super_admin_service_id}
        
        request = factory.put(f'/api/provider/categories/TEMPLATE_{t_cat.id}/', data, format='json')
        force_authenticate(request, user=user)
        response = view(request, pk=f"TEMPLATE_{t_cat.id}")
        
        print(f"Response: {response.status_code}")
        if response.status_code == 200:
            print("Success! Shadow category created.")
            # Verify Shadow
            shadow = ProviderCategory.objects.filter(name=f"{t_cat.name} (Customized)", provider=user).first()
            if shadow:
                print(f"Shadow Category Found: {shadow.id}")
            else:
                print("❌ Shadow Category NOT Found")
            
            # Verify Permission Deleted
            perm = ProviderCapabilityAccess.objects.filter(user=user, category_id=t_cat.super_admin_category_id).exists()
            if not perm:
                print("Permission correctly deleted (Template hidden)")
            else:
                print("❌ Permission still exists!")

    # ==========================================
    # TEST 2: DELETE TEMPLATE FACILITY (Hiding)
    # ==========================================
    t_fac = ProviderTemplateFacility.objects.first()
    if t_fac:
        print(f"\n--- Testing Delete Template Facility: {t_fac.name} ({t_fac.id}) ---")
        
        # Ensure permission exists
        ProviderCapabilityAccess.objects.get_or_create(
            user=user,
            facility_id=t_fac.super_admin_facility_id,
            defaults={"plan_id": "test", "can_view": True}
        )
        
        view = ProviderFacilityViewSet.as_view({'delete': 'destroy'})
        request = factory.delete(f'/api/provider/facilities/TEMPLATE_{t_fac.id}/')
        force_authenticate(request, user=user)
        response = view(request, pk=f"TEMPLATE_{t_fac.id}")
        
        print(f"Response: {response.status_code}")
        if response.status_code == 204:
            print("Success! Template facility hidden.")
            # Verify Permission Deleted
            perm = ProviderCapabilityAccess.objects.filter(user=user, facility_id=t_fac.super_admin_facility_id).exists()
            if not perm:
                print("Permission correctly deleted")
            else:
                print("❌ Permission still exists!")

if __name__ == "__main__":
    test_template_edit_delete()
