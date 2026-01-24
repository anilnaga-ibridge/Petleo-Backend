import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import ProviderRole

def check_permissions():
    role_name = "Allrounder" # Adjust based on user input logic if needed
    print(f"🔍 Searching for role: '{role_name}'...")

    roles = ProviderRole.objects.all()
    
    if not roles.exists():
        print("❌ No roles found in the database.")
        return

    print(f"📋 Found {roles.count()} roles in valid database:")
    for role in roles:
        print(f"\n🔹 Role: {role.name} (ID: {role.id})")
        print(f"   Provider: {role.provider}")
        
        caps = role.capabilities.all()
        if not caps.exists():
             print("   ⚠️ No capabilities assigned.")
        else:
            print(f"   📜 Capabilities ({caps.count()}):")
            for cap in caps:
                print(f"      - {cap.capability_key}")

if __name__ == "__main__":
    check_permissions()
