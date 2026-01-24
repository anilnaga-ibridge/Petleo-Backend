
import os
import django
import uuid
import time
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_admin_service.settings')
django.setup()

from dynamic_permissions.models import Capability, FeatureModule, PlanCapability, ProviderCapability
from plans_coupens.models import Plan
from plans_coupens.purchase_publish_wrapper import purchase_plan_and_publish
from admin_core.models import SuperAdmin, VerifiedUser

def run():
    print("🚀 Starting Dynamic Permission Verification Setup...")

    # 1. Create Capability
    cap_key = "VETERINARY_TEST_DYN"
    cap, created = Capability.objects.get_or_create(
        key=cap_key,
        defaults={
            "name": "Test Dynamic Capability",
            "description": "A capability created by auto-verification",
            "service_type": "VETERINARY"
        }
    )
    print(f"✅ Capability: {cap} (Created: {created})")

    # 2. Create Feature Module
    mod_key = "test_module_dyn"
    mod, created = FeatureModule.objects.get_or_create(
        key=mod_key,
        defaults={
            "capability": cap,
            "name": "Dynamic Test Module",
            "route": "test-dynamic-route",
            "icon": "tabler-flask"
        }
    )
    print(f"✅ FeatureModule: {mod} (Created: {created})")

    # 3. Create Plan
    plan_slug = "dynamic-test-plan"
    plan, created = Plan.objects.get_or_create(
        slug=plan_slug,
        defaults={
            "title": "Dynamic Test Plan",
            "target_type": "ORGANIZATION",
            "price": 10.00,
            "billing_cycle": "MONTHLY",
            "is_active": True
        }
    )
    print(f"✅ Plan: {plan} (Created: {created})")

    # 4. Link Capability to Plan
    pc, created = PlanCapability.objects.get_or_create(
        plan=plan,
        capability=cap
    )
    print(f"✅ PlanCapability Linked: {pc}")

    # 5. Find or Create User with VALID UUID
    test_uuid = str(uuid.uuid4())
    admin_email = f"test.provider.{test_uuid[:8]}@check.com"
    
    test_admin_user = SuperAdmin.objects.create(
        email=admin_email,
        contact="9999999999",
        auth_user_id=test_uuid,
        user_role="Organization"
    )
    test_admin_user.set_password("testpass")
    test_admin_user.save()
        
    print(f"👤 Using SuperAdmin User: {test_admin_user.email} (AuthID: {test_admin_user.auth_user_id})")
    
    # Ensure VerifiedUser exists for syncing (using same UUID)
    VerifiedUser.objects.create(
        auth_user_id=test_admin_user.auth_user_id,
        email=admin_email,
        role="organization",
        full_name="Test Dynamic Provider"
    )
    
    # 5.5 Publish USER_CREATED event to sync user to Service Provider Service
    from kafka_client.kafka_producer import publish_event
    publish_event(
        topic="organization_events", 
        event="USER_CREATED",
        payload={
            "auth_user_id": test_uuid,
            "full_name": "Test Dynamic Provider",
            "email": admin_email,
            "role": "organization",
            "phone_number": "9999999999"
        },
        service="super_admin"
    )
    print("📨 USER_CREATED Kafka Event Published.")
    time.sleep(2) # Give Kafka a moment

    # 6. Purchase Plan (Triggers Kafka)
    print("💰 Purchasing Plan...")
    purchased = purchase_plan_and_publish(test_admin_user, plan)
    print(f"✅ Purchased ID: {purchased.id}")
    print("📨 Kafka Event Published. Waiting for sync...")
    
    # Write auth_user_id to a temp file for the next script
    with open("test_auth_id.txt", "w") as f:
        f.write(str(test_admin_user.auth_user_id))

if __name__ == "__main__":
    run()
