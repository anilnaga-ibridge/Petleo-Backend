
import os
import django
import sys

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, ProviderCapabilityAccess, FeatureModule, Capability

def debug_access():
    print("--- Debugging Org Access ---")
    
    # search for Anil
    users = VerifiedUser.objects.filter(full_name__icontains="Anil")
    if not users.exists():
        print("No user found with name 'Anil'")
        return

    user = users.first()
    print(f"User: {user.full_name} ({user.auth_user_id})")
    print(f"Role: {user.role}")
    
    try:
        sp = ServiceProvider.objects.get(verified_user=user)
        print(f"ServiceProvider Type: {sp.provider_type}")
    except ServiceProvider.DoesNotExist:
        print("No ServiceProvider profile found!")
        return

    # Check Capabilities
    caps = ProviderCapabilityAccess.objects.filter(user=user)
    print(f"\nTotal Capabilities: {caps.count()}")
    if caps.exists():
        for cap in caps:
            print(f" - {cap.capability.key} (Plan: {cap.plan_id})")
    else:
        print(" -> NO CAPABILITIES FOUND. Use needs to purchase a plan?")

    # Check Feature Modules for Org Info
    print("\n--- Checking Feature Modules (Expected for Org) ---")
    expected_keys = ['ORG_ADMIN_CORE', 'CLINIC_MANAGEMENT', 'EMPLOYEE_MANAGEMENT', 'ROLE_MANAGEMENT']
    
    for key in expected_keys:
        exists = Capability.objects.filter(key=key).exists()
        print(f"Capability '{key}' exists in DB? {exists}")
        
        if exists:
            # Check if user has it
            user_has = caps.filter(capability__key=key).exists()
            print(f" -> User has '{key}'? {user_has}")
            
            # Check modules linked
            modules = FeatureModule.objects.filter(capability__key=key)
            for m in modules:
                print(f"    -> Linked Module: {m.name} (Route: {m.route})")

if __name__ == "__main__":
    debug_access()
