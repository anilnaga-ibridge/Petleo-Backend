import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser
from provider_dynamic_fields.models import LocalFieldDefinition, ProviderFieldValue

def debug_user(email):
    print(f"🔍 Debugging User: {email}")
    
    try:
        user = VerifiedUser.objects.get(email=email)
        print(f"✅ Found User: {user.full_name} ({user.auth_user_id})")
        print(f"   - Role: {user.role}")
        
        # Check for ALL targets
        targets = ["individual", "organization", "employee"]
        
        for target in targets:
            print(f"\n📂 Target: {target.upper()}")
            fields = LocalFieldDefinition.objects.filter(target=target).order_by('order')
            if not fields.exists():
                 print("   ❌ No fields found!")
                 continue

            field_ids = fields.values_list('id', flat=True)
            values = ProviderFieldValue.objects.filter(verified_user=user, field_id__in=field_ids)
            
            if values.exists():
                print(f"   💾 Saved Values: {values.count()}")
                for v in values:
                    try:
                        f_def = LocalFieldDefinition.objects.get(id=v.field_id)
                        print(f"      - {f_def.label} ({f_def.name}): {v.value}")
                    except LocalFieldDefinition.DoesNotExist:
                        print(f"      - UNKNOWN_FIELD_ID: {v.value}")
            else:
                print("   ⚠️ No saved values for this target.")

    except VerifiedUser.DoesNotExist:
        print("❌ User not found in Service Provider Service!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_user("raj@gmail.com")
