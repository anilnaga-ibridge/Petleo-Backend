
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from provider_dynamic_fields.models import ProviderTemplateCategory
from service_provider.models import ProviderRoleCapability

def verify_and_fix():
    print("🔍 Verifying System Keys vs Role Keys...")
    
    # 1. Check valid system keys from Templates
    valid_keys = set(ProviderTemplateCategory.objects.exclude(linked_capability__isnull=True).values_list('linked_capability', flat=True))
    print(f"✅ Found {len(valid_keys)} Valid System Keys (from Categories):")
    print(sorted(list(valid_keys)))
    
    # 2. Check for bad keys in Roles
    bad_keys_map = {
        "Grooming": "GROOMING",
        "Day Care": "DAYCARE",
        "Training": "TRAINING",
        "Trainning": "TRAINING", # Typo found in log
        "Boarding": "BOARDING",
        "Daycare": "DAYCARE"
    }
    
    print("\n🔍 Scanning ProviderRoleCapability for bad keys...")
    bad_caps = ProviderRoleCapability.objects.filter(capability_key__in=bad_keys_map.keys())
    
    if not bad_caps.exists():
        print("✅ No known bad keys found.")
        return

    print(f"⚠️  Found {bad_caps.count()} records with bad keys.")
    
    for cap in bad_caps:
        old_val = cap.capability_key
        new_val = bad_keys_map.get(old_val)
        
        print(f"   - Fixing {cap.provider_role.name}: '{old_val}' -> '{new_val}'")
        
        # Check if the correct one already exists for this role to avoid unique constraint error
        exists = ProviderRoleCapability.objects.filter(
            provider_role=cap.provider_role,
            capability_key=new_val
        ).exists()
        
        if exists:
            print("     (Duplicate exists, deleting bad record)")
            cap.delete()
        else:
            cap.capability_key = new_val
            cap.save()
            
    print("✅ Fix Complete.")

if __name__ == "__main__":
    verify_and_fix()
