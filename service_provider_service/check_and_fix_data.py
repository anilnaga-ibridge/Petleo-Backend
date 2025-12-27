import os
import django
import sys
import uuid
from django.utils import timezone

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider, OrganizationEmployee

USER_EMAIL = "nagaanil29@gmail.com"

print(f"🕵️‍♀️ Checking data for: {USER_EMAIL}")

try:
    user = VerifiedUser.objects.get(email=USER_EMAIL)
    provider = ServiceProvider.objects.get(verified_user=user)
    
    print(f"   User ID: {user.auth_user_id}")
    print(f"   Provider ID: {provider.id}")

    # 1. Check for orphaned employees (created by this user but no org linked)
    orphans = OrganizationEmployee.objects.filter(created_by=user.auth_user_id, organization__isnull=True)
    
    if orphans.exists():
        print(f"   ⚠️ Found {orphans.count()} orphaned employees. Linking them now...")
        for emp in orphans:
            emp.organization = provider
            emp.save()
            print(f"      🔗 Linked: {emp.full_name}")
    else:
        print("   ✅ No orphaned employees found.")

    # 2. Check if they have ANY employees now
    count = OrganizationEmployee.objects.filter(organization=provider).count()
    print(f"   📊 Current Employee Count: {count}")

    # 3. If 0, create a TEST employee
    if count == 0:
        print("   🆕 Creating a TEST employee for verification...")
        test_emp = OrganizationEmployee.objects.create(
            auth_user_id=uuid.uuid4(),
            organization=provider,
            full_name="Test Employee (Auto-Created)",
            email="test.auto@example.com",
            phone_number="9998887776",
            status="active",
            joined_at=timezone.now(),
            created_by=user.auth_user_id
        )
        print(f"   ✅ Created: {test_emp.full_name}")
    
except VerifiedUser.DoesNotExist:
    print("❌ User not found.")
except ServiceProvider.DoesNotExist:
    print("❌ Provider profile not found.")
except Exception as e:
    print(f"❌ Error: {e}")
