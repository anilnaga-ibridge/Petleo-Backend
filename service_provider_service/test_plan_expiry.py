import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription
from service_provider.views import get_my_permissions
from rest_framework.test import APIRequestFactory, force_authenticate

def test_expiry():
    email = "nagaanil29@gmail.com"
    try:
        user = VerifiedUser.objects.get(email=email)
        print(f"User: {user.email}")
        
        # 1. Verify Active State
        sub = user.subscription.first()
        print(f"Current Subscription: Active={sub.is_active}, End={sub.end_date}")
        
        factory = APIRequestFactory()
        request = factory.get('/api/provider/permissions/')
        force_authenticate(request, user=user)
        
        response = get_my_permissions(request)
        perms_count = len(response.data.get("permissions", []))
        print(f"Active Plan Permissions Count: {perms_count}")
        
        if perms_count == 0:
            print("❌ Error: Should have permissions when active!")
            return

        # 2. Expire the Plan
        print("\n--- Expiring Plan ---")
        sub.end_date = timezone.now() - timedelta(days=1)
        sub.save()
        print(f"Updated Subscription: Active={sub.is_active}, End={sub.end_date}")
        
        response = get_my_permissions(request)
        perms_count = len(response.data.get("permissions", []))
        print(f"Expired Plan Permissions Count: {perms_count}")
        
        if perms_count == 0:
            print("✅ Success: Permissions hidden for expired plan")
        else:
            print("❌ Failure: Permissions still visible for expired plan")
            
        # 3. Restore Plan
        print("\n--- Restoring Plan ---")
        sub.end_date = timezone.now() + timedelta(days=365)
        sub.save()
        print("Plan restored.")

    except VerifiedUser.DoesNotExist:
        print(f"User {email} not found")

if __name__ == "__main__":
    test_expiry()
