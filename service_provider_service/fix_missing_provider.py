import os
import django
import sys
import uuid

sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider

USER_EMAIL = "nagaanil29@gmail.com"

print(f"🔧 Fixing Missing ServiceProvider for: {USER_EMAIL}")

try:
    user = VerifiedUser.objects.get(email=USER_EMAIL)
    print(f"✅ Found VerifiedUser: {user.full_name} ({user.auth_user_id})")
    
    provider, created = ServiceProvider.objects.get_or_create(
        verified_user=user,
        defaults={
            "profile_status": "active",
            "is_fully_verified": True
        }
    )
    
    if created:
        print(f"✅ Created NEW ServiceProvider profile: {provider.id}")
    else:
        print(f"ℹ️ ServiceProvider profile already exists: {provider.id}")
        
except VerifiedUser.DoesNotExist:
    print(f"❌ VerifiedUser NOT FOUND for email: {USER_EMAIL}")
except Exception as e:
    print(f"❌ Error: {e}")
