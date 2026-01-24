
import os
import django
import time
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import FeatureModule, ProviderCapability, VerifiedUser, Capability

def run():
    print("🚀 Starting Dynamic Permission Verification Check...")
    
    # Read auth_user_id
    try:
        with open("../super_admin_service/test_auth_id.txt", "r") as f:
            auth_user_id = f.read().strip()
    except FileNotFoundError:
        print("❌ Auth ID file not found. Run setup script first.")
        return

    print(f"🔍 Checking for User: {auth_user_id}")
    
    # Wait loop
    max_retries = 10
    found = False
    
    for i in range(max_retries):
        try:
            user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
            caps = ProviderCapability.objects.filter(user=user, is_active=True)
            modules = FeatureModule.objects.all() # FeatureModules are global actually, synced from SA
            
            has_cap = caps.filter(capability__key="VETERINARY_TEST_DYN").exists()
            has_mod = modules.filter(key="test_module_dyn").exists()
            
            print(f"   Attempt {i+1}: Cap Found={has_cap}, Module Synced={has_mod}")
            
            if has_cap and has_mod:
                print("✅ SUCCESS: Dynamic Capability and Module are synced!")
                
                # Check specifics
                c = caps.get(capability__key="VETERINARY_TEST_DYN")
                m = modules.get(key="test_module_dyn")
                print(f"   > Capability: {c.capability.key}")
                print(f"   > Module: {m.name} -> {m.route}")
                found = True
                break
                
        except VerifiedUser.DoesNotExist:
             print(f"   Attempt {i+1}: User not found yet...")
        
        time.sleep(2)
        
    if not found:
        print("❌ FAILED: Timeout waiting for Kafka sync.")
        sys.exit(1)

if __name__ == "__main__":
    run()
