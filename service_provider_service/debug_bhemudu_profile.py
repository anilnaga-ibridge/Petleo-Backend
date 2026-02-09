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
            else:
                 print(f"   - Found {fields.count()} field definitions:")
                 for f in fields:
                     print(f"     * {f.label} ({f.name}) [Type: {f.field_type}]")
            
            # Check values for this user regardless of target logic
            field_ids = fields.values_list('id', flat=True)
            values = ProviderFieldValue.objects.filter(verified_user=user, field_id__in=field_ids)
            
            if values.exists():
                print(f"   💾 Saved Values: {values.count()}")
                for v in values:
                    # Manually look up field definition since there is no ForeignKey
                    try:
                        f_def = LocalFieldDefinition.objects.get(id=v.field_id)
                        f_name = f_def.name
                        f_label = f_def.label
                    except LocalFieldDefinition.DoesNotExist:
                        f_name = "UNKNOWN_FIELD"
                        f_label = "Unknown"
                        
                    print(f"      - {f_label} ({f_name}): {v.value}")
            else:
                print("   ⚠️ No saved values for this target.")

    except VerifiedUser.DoesNotExist:
        print("❌ User not found in Service Provider Service!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_user("bhemudu@gmail.com")
