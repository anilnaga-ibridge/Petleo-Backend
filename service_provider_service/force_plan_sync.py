"""
Force Full Plan Sync - Emergency Fix
This manually syncs ALL data that would normally come from a plan purchase Kafka event
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from service_provider.models import VerifiedUser, ProviderSubscription, AllowedService
from provider_dynamic_fields.models import (
    ProviderTemplateService, ProviderTemplateCategory, 
    ProviderTemplateFacility, ProviderCapabilityAccess, ProviderTemplatePricing
)
from django.utils import timezone
from django.db import transaction

def force_sync_plan_data(auth_user_id, plan_id="manual-emergency-sync"):
    """
    Manually sync all plan data for a user
    This simulates what the Kafka consumer would do
    """
    try:
        user = VerifiedUser.objects.get(auth_user_id=auth_user_id)
    except VerifiedUser.DoesNotExist:
        print(f"❌ User with auth_user_id '{auth_user_id}' not found")
        return
    except VerifiedUser.MultipleObjectsReturned:
        print(f"⚠️  Multiple users found with that criteria")
        user = VerifiedUser.objects.filter(auth_user_id=auth_user_id).first()
        print(f"   Using first match: {user.email}")
    
    print(f"\n{'='*60}")
    print(f"🔄 FORCE SYNCING PLAN DATA")
    print(f"📧 User: {user.email}")
    print(f"🆔 Auth ID: {user.auth_user_id}")
    print(f"{'='*60}\n")
    
    with transaction.atomic():
        # 1. Clear existing data
        print("🧹 Clearing old data...")
        ProviderCapabilityAccess.objects.filter(user=user).delete()
        AllowedService.objects.filter(verified_user=user).delete()
        user.permissions = []
        user.save()
        
        # 2. Get all template data
        services = ProviderTemplateService.objects.all()
        categories = ProviderTemplateCategory.objects.all()
        facilities = ProviderTemplateFacility.objects.all()
        
        print(f"📊 Template Data Available:")
        print(f"   Services: {services.count()}")
        print(f"   Categories: {categories.count()}")
        print(f"   Facilities: {facilities.count()}\n")
        
        # 3. Create ProviderCapabilityAccess records for ALL templates
        print("📝 Creating Capability Access records...")
        created_count = 0
        
        for service in services:
            for category in categories.filter(service=service):
                for facility in facilities.filter(category=category):
                    # Get pricing for this facility
                    pricing_rules = ProviderTemplatePricing.objects.filter(
                        service=service,
                        category=category,
                        facility=facility
                    )
                    
                    for pricing in pricing_rules:
                        ProviderCapabilityAccess.objects.create(
                            user=user,
                            plan_id=plan_id,
                            service_id=service.super_admin_service_id,
                            category_id=category.super_admin_category_id,
                            facility_id=facility.super_admin_facility_id,
                            pricing_id=pricing.super_admin_pricing_id,
                            can_view=True,
                            can_create=True,
                            can_edit=True,
                            can_delete=False
                        )
                        created_count += 1
            
            # 3.1 Also create AllowedService record
            AllowedService.objects.update_or_create(
                verified_user=user,
                service_id=service.super_admin_service_id,
                defaults={
                    'name': service.display_name,
                    'icon': service.icon or 'tabler-box'
                }
            )
            print(f"   🔓 Activated Service: {service.display_name} ({service.super_admin_service_id})")
        
        print(f"   ✅ Created {created_count} capability access records\n")
        
        # 4. Update user permissions from linked capabilities
        print("🔑 Updating user permissions...")
        linked_caps = categories.values_list('linked_capability', flat=True)
        linked_caps = [lc for lc in linked_caps if lc]
        
        if linked_caps:
            updated_perms = list(set(linked_caps))
            
            # Only add VETERINARY_CORE if veterinary capabilities exist
            vet_caps = [cap for cap in updated_perms if cap.startswith("VETERINARY_")]
            if vet_caps:
                if "VETERINARY_CORE" not in updated_perms:
                    updated_perms.append("VETERINARY_CORE")
                print(f"   🏥 Veterinary capabilities: {len(vet_caps)}")
                print(f"   ✅ Added VETERINARY_CORE")
            
            user.permissions = updated_perms
            user.save()
            print(f"   ✅ Set permissions: {len(updated_perms)} capabilities\n")
        
        # 5. Create subscription record
        print("📋 Creating subscription...")
        ProviderSubscription.objects.update_or_create(
            verified_user=user,
            defaults={
                'plan_id': plan_id,
                'is_active': True,
                'start_date': timezone.now(),
                'end_date': timezone.now() + timezone.timedelta(days=365)
            }
        )
        print(f"   ✅ Subscription created\n")
    
    print(f"{'='*60}")
    print(f"✅ SYNC COMPLETE!")
    print(f"{'='*60}\n")
    print(f"📊 Final Stats:")
    print(f"   User Permissions: {len(user.permissions)}")
    print(f"   Capability Records: {ProviderCapabilityAccess.objects.filter(user=user).count()}")
    print(f"   Has Subscription: {ProviderSubscription.objects.filter(verified_user=user, is_active=True).exists()}")
    print(f"\n💡 User should LOGOUT and LOGIN again to see changes")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python force_plan_sync.py <auth_user_id>")
        sys.exit(1)
    
    auth_user_id = sys.argv[1]
    force_sync_plan_data(auth_user_id)
