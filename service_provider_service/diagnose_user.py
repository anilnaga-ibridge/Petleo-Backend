"""
Quick Diagnostic & Resync Tool
Checks current state and optionally triggers a fresh permission sync
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription
from provider_dynamic_fields.models import (
    ProviderTemplateService, ProviderTemplateCategory, 
    ProviderTemplateFacility, ProviderCapabilityAccess
)

def diagnose_user(email_or_id):
    """Diagnose current user state"""
    # Find user
    if '@' in email_or_id:
        user = VerifiedUser.objects.filter(email=email_or_id).first()
    else:
        user = VerifiedUser.objects.filter(auth_user_id=email_or_id).first()
    
    if not user:
        print(f"❌ User '{email_or_id}' not found")
        return None
    
    print(f"\n{'='*60}")
    print(f"📧 User: {user.email}")
    print(f"🆔 Auth ID: {user.auth_user_id}")
    print(f"🔑 Permissions: {user.permissions}")
    print(f"{'='*60}\n")
    
    # Check subscription
    subscription = ProviderSubscription.objects.filter(verified_user=user, is_active=True).first()
    if subscription:
        print(f"📋 Active Subscription:")
        print(f"   Plan ID: {subscription.plan_id}")
        print(f"   Start: {subscription.start_date}")
        print(f"   End: {subscription.end_date}")
    else:
        print("⚠️  No active subscription found")
    
    # Check template data (global)
    print(f"\n🌐 Global Template Stats:")
    print(f"   Services: {ProviderTemplateService.objects.count()}")
    print(f"   Categories: {ProviderTemplateCategory.objects.count()}")
    print(f"   Facilities: {ProviderTemplateFacility.objects.count()}")
    
    # Check user-specific capability access
    cap_count = ProviderCapabilityAccess.objects.filter(user=user).count()
    print(f"\n👤 User-Specific Data:")
    print(f"   Capability Access Records: {cap_count}")
    
    if cap_count > 0:
        print(f"\n   Sample Capabilities:")
        for cap in ProviderCapabilityAccess.objects.filter(user=user)[:5]:
            print(f"     - Service: {cap.service_id}, Category: {cap.category_id}")
    
    # Check if this looks like a failed sync
    if len(user.permissions) == 1 and user.permissions[0] == "VETERINARY_CORE":
        print(f"\n⚠️  WARNING: User has ONLY VETERINARY_CORE permission")
        print(f"   This indicates a FAILED plan purchase (old bug)")
        print(f"   Solution: Re-purchase plan or run manual resync")
    elif cap_count == 0:
        print(f"\n⚠️  WARNING: User has NO capability access records")
        print(f"   This means no plan data was synced")
        print(f"   Solution: Purchase a plan in Super Admin")
    
    return user

def manual_resync(user_email_or_id):
    """Manually trigger a permission recalculation"""
    user = diagnose_user(user_email_or_id)
    if not user:
        return
    
    print(f"\n{'='*60}")
    print(f"🔄 MANUAL RESYNC")
    print(f"{'='*60}\n")
    
    # Get template categories (these are synced from Super Admin via Kafka)
    template_cats = ProviderTemplateCategory.objects.all()
    linked_caps = [cat.linked_capability for cat in template_cats if cat.linked_capability]
    
    if not linked_caps:
        print("⚠️  No template categories found")
        print("   This means Super Admin hasn't synced any services yet")
        print("   OR the plan purchase Kafka event hasn't been processed")
        return
    
    print(f"📋 Found {len(set(linked_caps))} unique linked capabilities:")
    for cap in set(linked_caps):
        print(f"   - {cap}")
    
    # Calculate new permissions
    updated_perms = list(set(linked_caps))
    
    # Only add VETERINARY_CORE if veterinary capabilities exist
    vet_caps = [cap for cap in updated_perms if cap.startswith("VETERINARY_")]
    if vet_caps:
        if "VETERINARY_CORE" not in updated_perms:
            updated_perms.append("VETERINARY_CORE")
        print(f"\n🏥 Veterinary capabilities detected: {vet_caps}")
        print(f"   ✅ VETERINARY_CORE will be included")
    else:
        print(f"\n⏭️  No veterinary capabilities found")
        print(f"   VETERINARY_CORE will NOT be added")
    
    # Update user
    user.permissions = updated_perms
    user.save()
    
    print(f"\n✅ User permissions updated to: {updated_perms}")
    print(f"\n💡 User should logout and login again to see changes")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Diagnose: python diagnose_user.py <email_or_auth_user_id>")
        print("  Resync:   python diagnose_user.py <email_or_auth_user_id> --resync")
        sys.exit(1)
    
    user_id = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == '--resync':
        manual_resync(user_id)
    else:
        diagnose_user(user_id)
