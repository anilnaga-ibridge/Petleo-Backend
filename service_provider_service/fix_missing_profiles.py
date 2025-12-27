import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/PraveenWorks/Anil Works/Petleo-Backend/service_provider_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider

def fix_missing_profiles():
    print("--- Fixing Missing ServiceProvider Profiles ---")
    
    # Find all users with role 'organization' or 'serviceprovider'
    users = VerifiedUser.objects.filter(role__in=['organization', 'serviceprovider'])
    print(f"Found {users.count()} potential providers.")
    
    fixed_count = 0
    for user in users:
        provider, created = ServiceProvider.objects.get_or_create(verified_user=user)
        if created:
            print(f"✅ Created missing profile for {user.email} (Auth ID: {user.auth_user_id})")
            provider.business_name = user.full_name or "My Business"
            provider.save()
            fixed_count += 1
        else:
            # print(f"  OK: {user.email}")
            pass
            
    print(f"--- Done. Fixed {fixed_count} users. ---")

if __name__ == "__main__":
    fix_missing_profiles()
