"""
Manual Plan Re-Sync Script

This script triggers a manual re-sync of permissions for a specific user,
forcing the Kafka consumer to re-process the plan and apply the latest fixes.

Usage:
    python manual_resync.py <user_email_or_auth_user_id>
"""

import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription
from provider_dynamic_fields.models import ProviderTemplateService, ProviderTemplateCategory

def resync_user_permissions(identifier):
    """Manually clear and re-sync permissions for a user"""
    
    # Find user
    try:
        if '@' in identifier:
            user = VerifiedUser.objects.get(email=identifier)
        else:
            user = VerifiedUser.objects.get(auth_user_id=identifier)
    except VerifiedUser.DoesNotExist:
        print(f"❌ User {identifier} not found")
        return
    
    print(f"🔍 Found user: {user.email} ({user.auth_user_id})")
    
    # Get current subscription
    try:
        subscription = ProviderSubscription.objects.get(verified_user=user, is_active=True)
        print(f"📋 Current Plan: {subscription.plan_id}")
    except ProviderSubscription.DoesNotExist:
        print("⚠️ No active subscription found")
        subscription = None
    
    # Clear current permissions
    print("🧹 Clearing current permissions...")
    user.permissions = []
    user.save()
    
    # Calculate new permissions from templates
    print("🔄 Recalculating permissions from templates...")
    
    # Get all template categories
    template_cats = ProviderTemplateCategory.objects.all()
    linked_caps = [cat.linked_capability for cat in template_cats if cat.linked_capability]
    
    if linked_caps:
        updated_perms = list(set(linked_caps))
        
        # Only add VETERINARY_CORE if veterinary capabilities exist
        has_vet = any(cap.startswith("VETERINARY_") for cap in updated_perms)
        if has_vet and "VETERINARY_CORE" not in updated_perms:
            updated_perms.append("VETERINARY_CORE")
            print(f"✅ Added VETERINARY_CORE (vet capabilities detected)")
        
        user.permissions = updated_perms
        user.save()
        
        print(f"✅ Updated permissions: {updated_perms}")
    else:
        print("⚠️ No linked capabilities found in templates")
    
    print("\n✅ Manual re-sync complete!")
    print(f"💡 User should log out and log back in to see changes")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_resync.py <user_email_or_auth_user_id>")
        sys.exit(1)
    
    resync_user_permissions(sys.argv[1])
