"""
fix_provider_types.py
======================
One-time script to correct ServiceProvider.provider_type for all users
where the VerifiedUser.role indicates a different type than what's stored.

Run with:
  cd /Users/PraveenWorks/Anil\ Works/Petleo-Backend/service_provider_service
  source venv/bin/activate  (if applicable)
  python fix_provider_types.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
django.setup()

from service_provider.models import VerifiedUser, ServiceProvider

print("=" * 60)
print("🔧 Fixing Provider Types")
print("=" * 60)

fixed = 0
created = 0
skipped = 0

for user in VerifiedUser.objects.all():
    role = (user.role or "").lower()
    
    # Determine expected provider_type based on user role
    if role in ["organization", "serviceprovider", "provider"]:
        expected_type = "ORGANIZATION"
    elif role == "individual":
        expected_type = "INDIVIDUAL"
    else:
        # Employees, Super Admins, Pet Owners don't need this fixed
        skipped += 1
        continue
    
    # Get or create ServiceProvider record
    provider, was_created = ServiceProvider.objects.get_or_create(
        verified_user=user,
        defaults={"provider_type": expected_type}
    )
    
    if was_created:
        print(f"✅ Created ServiceProvider ({expected_type}) for: {user.email} [{user.role}]")
        created += 1
    elif provider.provider_type != expected_type:
        old_type = provider.provider_type
        provider.provider_type = expected_type
        provider.save(update_fields=["provider_type"])
        print(f"🔧 Fixed: {user.email} [{user.role}] => {old_type} → {expected_type}")
        fixed += 1
    else:
        print(f"✓ OK: {user.email} [{user.role}] => {provider.provider_type}")

print()
print("=" * 60)
print(f"✅ Done! Fixed: {fixed} | Created: {created} | Skipped: {skipped}")
print("=" * 60)
