
import os
import django
import sys
from django.utils import timezone

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ['DJANGO_SETTINGS_MODULE'] = 'service_provider_service.settings'
django.setup()

from service_provider.models import ServiceProvider, VerifiedUser, ProviderSubscription
from provider_cart.models import PurchasedPlan

def fix_data():
    print("🔧 Fixing Provider Data...")
    
    # 1. Activate Raj Bethi
    raj = ServiceProvider.objects.filter(verified_user__email="raj@gmail.com").first()
    if raj:
        print(f"Updating Raj Bethi ({raj.verified_user.email}) to active/verified...")
        raj.profile_status = "active"
        raj.is_fully_verified = True
        raj.save()
        print("✅ Raj Bethi updated.")
    else:
        print("⚠️ Raj Bethi not found.")

    # 2. Give Yadagiri a subscription if missing
    yada_user = VerifiedUser.objects.filter(email="yadagiri@gmail.com").first()
    if yada_user:
        yada_sp = ServiceProvider.objects.filter(verified_user=yada_user).first()
        if yada_sp:
            print(f"Updating Yadagiri ({yada_user.email}) subscription...")
            # Use filter to avoid MultipleObjectsReturned
            sub = ProviderSubscription.objects.filter(verified_user=yada_user).first()
            if sub:
                sub.plan_id = "manual-fix-plan"
                sub.is_active = True
                sub.save()
            else:
                ProviderSubscription.objects.create(
                    verified_user=yada_user,
                    plan_id="manual-fix-plan",
                    start_date=timezone.now(),
                    is_active=True
                )
            print("✅ Yadagiri subscription updated.")
    else:
        print("⚠️ Yadagiri not found.")

    # 3. Activate Prem (Individual)
    prem_user = VerifiedUser.objects.filter(email="prem@gmail.com").first()
    if prem_user:
        print(f"Updating Prem ({prem_user.email}) to active/verified...")
        prem_sp, _ = ServiceProvider.objects.get_or_create(verified_user=prem_user)
        prem_sp.profile_status = "active"
        prem_sp.is_fully_verified = True
        prem_sp.save()
        
        # Use filter to avoid MultipleObjectsReturned
        sub = ProviderSubscription.objects.filter(verified_user=prem_user).first()
        if sub:
            sub.plan_id = "manual-fix-plan-ind"
            sub.is_active = True
            sub.save()
        else:
            ProviderSubscription.objects.create(
                verified_user=prem_user,
                plan_id="manual-fix-plan-ind",
                start_date=timezone.now(),
                is_active=True
            )
        print("✅ Prem updated.")
    else:
        print("⚠️ Prem not found.")

if __name__ == "__main__":
    fix_data()
