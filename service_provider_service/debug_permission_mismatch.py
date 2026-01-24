
import os
import sys
import django
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from django.utils import timezone
from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee, ProviderRole
from provider_dynamic_fields.models import (
    ProviderCapabilityAccess, 
    ProviderTemplateCategory
)
from service_provider.utils import _build_permission_tree

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

TARGET_EMAIL = "nagaanil29@gmail.com"
TARGET_ROLE_NAME = "AllRounder"

def debug_mismatch():
    print(f"\n🚀 STARTING PERMISSION MISMATCH ANALYSIS FOR: {TARGET_EMAIL}")
    print("--------------------------------------------------")
    
    # --------------------------------------------------
    # STEP 1: COLLECT DATA
    # --------------------------------------------------
    print("\n[STEP 1] COLLECTING PROVIDER & PLAN DATA")
    try:
        provider_user = VerifiedUser.objects.get(email=TARGET_EMAIL)
    except VerifiedUser.DoesNotExist:
        print(f"❌ User {TARGET_EMAIL} not found!")
        return

    print(f"✅ Found Provider User: {provider_user.full_name} ({provider_user.auth_user_id})")

    # Fetch Subscription
    subs = provider_user.purchased_plans.filter(is_active=True)
    if not subs.exists():
        print("❌ NO ACTIVE SUBSCRIPTION FOUND!")
        # Proceeding anyway to check capabilities
    else:
        for s in subs:
            print(f"📦 Active Plan: {s.plan_title} (End: {s.end_date})")

    # Fetch ProviderCapabilityAccess
    # These are the RAW category/service IDs
    access_records = ProviderCapabilityAccess.objects.filter(user=provider_user)
    print(f"🔑 ProviderCapabilityAccess Records: {access_records.count()}")
    
    # Calculate PLAN CAPABILITIES (Upper Bound)
    # Using the exact logic from VerifiedUser.get_all_plan_capabilities
    cat_ids = access_records.filter(category_id__isnull=False).values_list('category_id', flat=True)
    
    linked_caps = ProviderTemplateCategory.objects.filter(
        super_admin_category_id__in=cat_ids
    ).exclude(linked_capability__isnull=True).values_list('linked_capability', flat=True)
    
    plan_caps = set(linked_caps)
    print(f"🏛️  PLAN CAPABILITIES (Derived from {len(cat_ids)} categories):")
    print(f"   {sorted(list(plan_caps))}")

    # --------------------------------------------------
    # STEP 2: TEMPLATE MAPPING CHECK
    # --------------------------------------------------
    print("\n[STEP 2] CHECKING TEMPLATE LINKAGES")
    # Check if any categories are missing linked_capability
    cats_without_links = ProviderTemplateCategory.objects.filter(
        super_admin_category_id__in=cat_ids,
        linked_capability__isnull=True
    )
    if cats_without_links.exists():
        print(f"⚠️  WARNING: {cats_without_links.count()} Categories have NO linked_capability:")
        for c in cats_without_links[:5]:
            print(f"   - {c.name} (ID: {c.super_admin_category_id})")
    else:
        print("✅ All Plan Categories have valid linked_capability mappings.")

    # --------------------------------------------------
    # STEP 3: CUSTOM ROLE DATA
    # --------------------------------------------------
    print("\n[STEP 3] CUSTOM ROLE DATA")
    try:
        sp_profile = ServiceProvider.objects.get(verified_user=provider_user)
        role = ProviderRole.objects.get(provider=sp_profile, name__iexact=TARGET_ROLE_NAME)
        print(f"✅ Found Role '{role.name}' (ID: {role.id})")
        
        role_caps = set(role.capabilities.values_list("capability_key", flat=True))
        print(f"👮 Role Capabilities ({len(role_caps)}):")
        print(f"   {sorted(list(role_caps))}")
        
        # Check Subset
        missing_from_plan = role_caps - plan_caps
        if missing_from_plan:
            print(f"❌ ROLE EXCEEDS PLAN! invalid keys: {missing_from_plan}")
        else:
            print("✅ Role is a valid subset of the Plan.")

    except Exception as e:
        print(f"❌ Failed to fetch Custom Role: {e}")
        return

    # --------------------------------------------------
    # STEP 4: EMPLOYEE ASSIGNMENT
    # --------------------------------------------------
    print("\n[STEP 4] EMPLOYEE ASSIGNMENT")
    employees = role.employees.all()
    if not employees.exists():
        print("❌ No employees assigned to this role.")
        return
    
    target_employee = employees.first()
    print(f"👤 Analyzing First Employee: {target_employee.full_name} ({target_employee.email})")
    print(f"   Auth ID: {target_employee.auth_user_id}")
    print(f"   Assigned Role: {target_employee.provider_role.name}")

    # --------------------------------------------------
    # STEP 5: RUNTIME RESOLUTION (get_final_permissions)
    # --------------------------------------------------
    print("\n[STEP 5] RUNTIME RESOLUTION")
    
    # Simulate intersection
    final_caps = target_employee.get_final_permissions() # This uses the strict logic we added
    final_caps_set = set(final_caps)
    
    print(f"🏁 Final Calculated Permissions ({len(final_caps_set)}):")
    print(f"   {sorted(list(final_caps_set))}")
    
    # Diff
    if len(final_caps_set) < len(role_caps):
        lost_caps = role_caps - final_caps_set
        print(f"📉 LOSS DETECTED: {len(lost_caps)} capabilities removed by intersection:")
        print(f"   {lost_caps}")
        print("   (These are in the Role but NOT in the Plan)")
    else:
        print("✅ No capabilities lost during intersection (Role ⊆ Plan).")

    # --------------------------------------------------
    # STEP 6: SIDEBAR INJECTION SIMULATION
    # --------------------------------------------------
    print("\n[STEP 6] SIDEBAR INJECTION CHECK")
    
    # We copy the keys from views.py manually to verify
    simple_services = {
        "GROOMING": "Grooming",
        "DAYCARE": "Daycare",
        "TRAINING": "Training",
        "BOARDING": "Boarding",
        "VETERINARY_VISITS": "Visits",
        "VETERINARY_VITALS": "Vitals",
        "VETERINARY_PRESCRIPTIONS": "Prescriptions",
    }
    
    print("Checking visibility matches:")
    for key, name in simple_services.items():
        has_it = key in final_caps_set
        status = "✅ VISIBLE" if has_it else "❌ HIDDEN "
        print(f"   {status} | {key:<25} ({name})")
        
        # Heuristic check
        if not has_it and key in role_caps:
             print(f"      To confirm: Role has it, but it was filtered out by Plan.")

if __name__ == "__main__":
    debug_mismatch()
