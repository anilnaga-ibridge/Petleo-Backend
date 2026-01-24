
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
from kafka_client.kafka_producer import publish_event

def setup_scenario():
    print("\n📦 --- SETUP: CREATING PLANS & CAPABILITIES ---")
    
    # 1. Plan A (Gold) -> CAP_A (Feature A)
    # 2. Plan B (Silver) -> CAP_B (Feature B)
    
    cap_a, _ = Capability.objects.get_or_create(key="CAP_GOLD", defaults={"name": "Gold Capability"})
    mod_a, _ = FeatureModule.objects.get_or_create(key="MOD_GOLD", defaults={"capability": cap_a, "name": "Gold Board", "route": "gold-board"})
    
    cap_b, _ = Capability.objects.get_or_create(key="CAP_SILVER", defaults={"name": "Silver Capability"})
    mod_b, _ = FeatureModule.objects.get_or_create(key="MOD_SILVER", defaults={"capability": cap_b, "name": "Silver Board", "route": "silver-board"})
    
    plan_a, _ = Plan.objects.get_or_create(slug="plan-gold", defaults={"title": "Gold Plan", "target_type": "ORGANIZATION", "price": 100})
    plan_b, _ = Plan.objects.get_or_create(slug="plan-silver", defaults={"title": "Silver Plan", "target_type": "ORGANIZATION", "price": 50})
    
    # Link: A->A, B->B (Strict Separation)
    PlanCapability.objects.get_or_create(plan=plan_a, capability=cap_a)
    PlanCapability.objects.get_or_create(plan=plan_b, capability=cap_b)
    
    # Ensure NO cross linking
    PlanCapability.objects.filter(plan=plan_a, capability=cap_b).delete()
    PlanCapability.objects.filter(plan=plan_b, capability=cap_a).delete()
    
    print(f"✅ Plan A (Gold) has CAP_GOLD. Modules: {[m.name for m in cap_a.modules.all()]}")
    print(f"✅ Plan B (Silver) has CAP_SILVER. Modules: {[m.name for m in cap_b.modules.all()]}")
    
    return plan_a, plan_b

def create_user_and_purchase(plan, suffix):
    print(f"\n👤 --- USER {suffix}: PURCHASE FLOW ---")
    
    # Create User
    test_uuid = str(uuid.uuid4())
    email = f"user.{suffix.lower()}.{test_uuid[:4]}@test.com"
    
    admin_user = SuperAdmin.objects.create(
        email=email,
        contact="9999999999",
        auth_user_id=test_uuid,
        user_role="Organization"
    )
    admin_user.set_password("testpass")
    admin_user.save()
    
    # Create VerifiedUser (for sync)
    VerifiedUser.objects.create(
        auth_user_id=test_uuid,
        email=email,
        role="organization",
        full_name=f"User {suffix}"
    )
    
    # Publish USER_CREATED
    print(f"📨 Publishing USER_CREATED for User {suffix}...")
    publish_event(
        topic="organization_events", 
        event="USER_CREATED",
        payload={
            "auth_user_id": test_uuid,
            "full_name": f"User {suffix}",
            "email": email,
            "role": "organization",
            "phone_number": "9999999999"
        },
        service="super_admin"
    )
    time.sleep(1) # Kafka delay
    
    # Purchase
    print(f"💰 Purchasing {plan.title} for User {suffix}...")
    purchase_plan_and_publish(admin_user, plan)
    print(f"✅ Purchase Complete via Wrapper (Kafka Triggered)")
    
    return test_uuid

def run():
    print("🚀 STARTING MULTI-TENANT VERIFICATION")
    
    plan_a, plan_b = setup_scenario()
    
    user_a_id = create_user_and_purchase(plan_a, "A")
    user_b_id = create_user_and_purchase(plan_b, "B")
    
    # Save IDs for step 2
    with open("verify_ids.txt", "w") as f:
        f.write(f"{user_a_id}\n{user_b_id}")
    
    print("\n📋 IDs saved to verify_ids.txt")
    print("⏳ Waiting for Kafka propagation...")

if __name__ == "__main__":
    run()
