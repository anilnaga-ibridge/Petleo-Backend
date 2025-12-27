import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription, AllowedService
from provider_dynamic_fields.models import ProviderCapabilityAccess

def debug_user():
    phone = "9014994286"
    print(f"--- Debugging User with Phone: {phone} ---")
    
    try:
        user = VerifiedUser.objects.get(phone_number=phone)
        print(f"✅ User Found: {user.full_name} ({user.email})")
        print(f"   ID: {user.auth_user_id}")
        
        # 1. Check Subscription
        subs = user.subscription.all()
        print(f"✅ Found {subs.count()} Subscriptions:")
        for sub in subs:
            print(f"   - Plan={sub.plan_id}, Active={sub.is_active}, Start={sub.start_date}, End={sub.end_date}")
            
        # 2. Check Permissions
        perms = ProviderCapabilityAccess.objects.filter(user=user)
        print(f"ℹ️ Permissions Count: {perms.count()}")
        for p in perms[:5]: # Print first 5
            print(f"   - Svc: {p.service_id}, Cat: {p.category_id}, View: {p.can_view}")
        
        # 3. Check Allowed Services
        allowed_count = AllowedService.objects.filter(verified_user=user).count()
        print(f"ℹ️ Allowed Services Count: {allowed_count}")
        
        if allowed_count > 0:
            services = AllowedService.objects.filter(verified_user=user)
            for s in services:
                print(f"   - {s.name}")
                
    except VerifiedUser.DoesNotExist:
        print(f"❌ User with phone {phone} not found")

    # Check for duplicate emails
    email = "nagaanil29@gmail.com"
    users_by_email = VerifiedUser.objects.filter(email=email)
    print(f"\n--- Checking for Duplicate Emails ({email}) ---")
    print(f"Count: {users_by_email.count()}")
    for u in users_by_email:
        print(f" - ID: {u.auth_user_id}, Phone: {u.phone_number}, Role: {u.role}")

    # Check Employee Table
    from service_provider.models import OrganizationEmployee
    employees = OrganizationEmployee.objects.filter(email=email)
    print(f"\n--- Checking Employee Records ({email}) ---")
    print(f"Count: {employees.count()}")
    for e in employees:
        print(f" - Org: {e.organization}, Status: {e.status}")

    # Check ServiceProvider Profile
    from service_provider.models import ServiceProvider
    try:
        profile = ServiceProvider.objects.get(verified_user=user)
        print(f"\n--- Checking Provider Profile ---")
        print(f"Status: {profile.profile_status}")
        print(f"Fully Verified: {profile.is_fully_verified}")
    except ServiceProvider.DoesNotExist:
        print("\n❌ No ServiceProvider profile found!")

    # Generate Token
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    print(f"\n--- JWT Token ---")
    print(f"Access: {str(refresh.access_token)}")

if __name__ == "__main__":
    debug_user()
