
import os
import django
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import FeatureModule, ProviderCapability, VerifiedUser

def run():
    print("\n🕵️ --- VERIFICATION: CHECKING SYNC & PRIVACY ---")
    
    try:
        with open("../super_admin_service/verify_ids.txt", "r") as f:
            ids = f.read().strip().split("\n")
            if len(ids) < 2:
                print("❌ Not enough IDs found.")
                return
            user_a_id, user_b_id = ids[0].strip(), ids[1].strip()
    except FileNotFoundError:
        print("❌ ID file not found. Run setup first.")
        return

    print(f"User A ID: {user_a_id}")
    print(f"User B ID: {user_b_id}")
    
    # Wait for Sync (Polling)
    time.sleep(3) 
    
    verify_user(user_a_id, "User A", should_have=["CAP_GOLD"], should_NOT_have=["CAP_SILVER"])
    verify_user(user_b_id, "User B", should_have=["CAP_SILVER"], should_NOT_have=["CAP_GOLD"])

def verify_user(auth_id, label, should_have, should_NOT_have):
    print(f"\n🔍 Checking {label} ({auth_id})...")
    
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_id)
        caps = ProviderCapability.objects.filter(user=user, is_active=True)
        keys = [c.capability.key for c in caps]
        
        print(f"   > Found Capabilities: {keys}")
        
        # Positive Check
        for k in should_have:
            if k in keys:
                print(f"   ✅ Correctly has {k}")
            else:
                print(f"   ❌ MISSING expected capability {k}")
        
        # Negative Check (Privacy)
        for k in should_NOT_have:
            if k in keys:
                print(f"   ❌ LEAK DETECTED: User has {k} but SHOULD NOT!")
            else:
                print(f"   ✅ Correctly does NOT have {k}")
                
        # Check Modules
        # FeatureModules are global but filtered by capability.
        # But we can check if ProviderCapability links are correct.
        
    except VerifiedUser.DoesNotExist:
        print(f"   ❌ User not found in Service Provider DB (Sync Failed?)")

if __name__ == "__main__":
    run()
