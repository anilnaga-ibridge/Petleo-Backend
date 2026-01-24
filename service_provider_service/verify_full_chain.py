
import os
import sys
import django
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, OrganizationEmployee
from service_provider.utils import _build_permission_tree

def verify_full_chain():
    TARGET_EMAIL = "nagaanil29@gmail.com" # The Org User
    # But wait, the issue is for the EMPLOYEE.
    # I need to find the employee email.
    
    # Let's find the employee for this org again.
    org_user = VerifiedUser.objects.get(email=TARGET_EMAIL)
    # Find employee assigned to "AllRounder"
    # From previous debug: eswar (eswar@gmail.com)
    
    EMP_EMAIL = "eswar@gmail.com"
    
    print(f"🚀 VERIFYING FULL CHAIN FOR EMPLOYEE: {EMP_EMAIL}")
    
    try:
        user = VerifiedUser.objects.get(email=EMP_EMAIL)
    except VerifiedUser.DoesNotExist:
        print("❌ Employee not found")
        return

    # --------------------------------------------------
    # REPLICATE VIEWS.PY LOGIC
    # --------------------------------------------------
    
    # 1. Build Tree (Should be empty-ish if emp has no direct access records, but let's see)
    # Wait, employees DON'T have ProviderCapabilityAccess usually unless assigned individually?
    # No, OrganizationEmployee permissions are virtual?
    # OR does "assign_plan_permissions_to_user" run for employees?
    # NO. Employees get permissions dynamically via Role.
    
    # So _build_permission_tree(user) will likely return [] for an employee?
    # Let's verify.
    permissions_list = _build_permission_tree(user)
    print(f"1. _build_permission_tree items: {len(permissions_list)}")
    
    # 2. Get User Caps (Intersection)
    user_caps = set()
    try:
        emp = OrganizationEmployee.objects.get(auth_user_id=user.auth_user_id)
        user_caps = set(emp.get_final_permissions())
        print(f"2. User Caps Intersection ({len(user_caps)}): {sorted(list(user_caps))}")
    except OrganizationEmployee.DoesNotExist:
        print("❌ Not an employee")
    
    # 3. Inject Simple Services
    simple_services = {
        "GROOMING": {"name": "Grooming", "icon": "tabler-cut"},
        "DAYCARE": {"name": "Daycare", "icon": "tabler-bone"},
        "TRAINING": {"name": "Training", "icon": "tabler-school"},
        "BOARDING": {"name": "Boarding", "icon": "tabler-home"},
        "VETERINARY_VISITS": {"name": "Visits", "icon": "tabler-calendar"},
        "VETERINARY_VITALS": {"name": "Vitals", "icon": "tabler-activity"},
        "VETERINARY_PRESCRIPTIONS": {"name": "Prescriptions", "icon": "tabler-pill"},
        "VETERINARY_LABS": {"name": "Lab Orders", "icon": "tabler-microscope"},
        # ... others
    }
    
    injected = []
    for key, meta in simple_services.items():
        if key in user_caps:
            # Check for duplicates
            if not any(p.get('service_key') == key for p in permissions_list):
                permissions_list.append({
                    "service_id": key,
                    "service_name": meta["name"],
                    "service_key": key,
                    "can_view": True
                })
                injected.append(key)
    
    print(f"3. Injected Services: {injected}")
    
    # --------------------------------------------------
    # FINAL OUTPUT CHECK
    # --------------------------------------------------
    print("\n🏁 FINAL API RESPONSE PREVIEW (Services):")
    for p in permissions_list:
        print(f"   - Name: {p.get('service_name'):<20} | Key: {p.get('service_key'):<20} | ID: {p.get('service_id')}")

    # Check specifically for Grooming
    has_grooming = any(p.get('service_key') == "GROOMING" for p in permissions_list)
    print(f"\n📢 HAS GROOMING? {'YES' if has_grooming else 'NO'}")

if __name__ == "__main__":
    verify_full_chain()
