
import sys
from service_provider.models import VerifiedUser, FeatureModule, ProviderCapability
from service_provider.views import MyAccessView
from django.test import RequestFactory

def verify(auth_id, label, expect, forbid):
    print(f"\n🔍 Checking {label} ({auth_id})...")
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_id)
    except VerifiedUser.DoesNotExist:
        print("   ❌ User not found")
        return

    # Manual logic check mimicking View
    # 1. Get Active Caps
    caps = ProviderCapability.objects.filter(user=user, is_active=True).values_list('capability__key', flat=True)
    
    # 2. Get Modules
    modules = MyAccessView()._get_modules_for_user(user)
    routes = [m['route'] for m in modules]
    
    print(f"   > Active Caps: {list(caps)}")
    print(f"   > Access Modules: {routes}")
    
    if expect in routes:
        print(f"   ✅ Correctly sees {expect}")
    else:
        print(f"   ❌ MISSING {expect}")
        
    if forbid in routes:
        print(f"   ❌ ERROR: Sees forbidden {forbid}")
    else:
        print(f"   ✅ Correctly blocked from {forbid}")

verify('2e042be2-4540-45bc-96cb-d62bc48eb582', 'User A', 'gold-board', 'silver-board')
verify('ced2289b-db80-436b-91cb-30dd09537752', 'User B', 'silver-board', 'gold-board')
    