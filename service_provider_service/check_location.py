import os
import django
import sys
import json

# Set up Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser, BillingProfile
from provider_dynamic_fields.models import ProviderFieldValue, LocalFieldDefinition

def sync_provider_location(email="anil.naga@ibridge.digital"):
    print(f"\n🔄 Syncing location for {email}...")
    try:
        user = VerifiedUser.objects.get(email=email)
        # Find Location field
        field_defs = LocalFieldDefinition.objects.filter(name="Location")
        val_obj = ProviderFieldValue.objects.filter(
            verified_user=user, 
            field_id__in=field_defs.values_list('id', flat=True)
        ).first()
        
        if val_obj and val_obj.value:
            billing, _ = BillingProfile.objects.get_or_create(verified_user=user)
            billing.contact = val_obj.value
            billing.save()
            print(f"✅ Synced: {val_obj.value}")
        else:
            print("⚠️ No Location value found to sync.")
    except Exception as e:
        print(f"❌ Sync Error: {e}")

def check_provider_location(email="anil.naga@ibridge.digital"):
    print(f"\n{'='*100}")
    print(f"{'PROVIDER LOCATION DATA CHECK':^100}")
    print(f"{'='*100}\n")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        provider = ServiceProvider.objects.get(verified_user=user)
        print(f"🏥 Provider: {user.full_name} ({user.email})")
        
        # 1. Billing Profile
        print("\n💳 Billing Profile:")
        try:
            bp = user.billing_profile
            print(f"   ├─ Contact (City): {bp.contact}")
            print(f"   ├─ State: {bp.state}")
            print(f"   └─ Address: {bp.address}")
        except BillingProfile.DoesNotExist:
            print("   ⚠️ No Billing Profile found.")
            
        # 2. Dynamic Fields
        print("\n⚙️ Dynamic Fields (Location-related):")
        field_values = ProviderFieldValue.objects.filter(verified_user=user)
        for val in field_values:
            try:
                fd = LocalFieldDefinition.objects.get(id=val.field_id)
                if fd.name.lower() in ["location", "city", "state"]:
                    print(f"   ├─ Field: {fd.name} ({fd.label}) -> {val.value}")
            except LocalFieldDefinition.DoesNotExist:
                pass
            
        # 3. Test the util function
        from service_provider.utils import get_user_dynamic_location
        dynamic_loc = get_user_dynamic_location(user)
        print(f"\n🚀 Utils get_user_dynamic_location: {dynamic_loc}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    sync_provider_location()
    check_provider_location()
