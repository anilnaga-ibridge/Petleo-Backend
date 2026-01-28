
import os
import sys
import django
import json
import time
from django.conf import settings

# Setup Django if not already configured
if not settings.configured:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_provider_service.settings")
    django.setup()

from kafka import KafkaProducer
from service_provider.models import VerifiedUser, OrganizationEmployee

def force_sync():
    print("🚀 Starting Force Permission Sync...")

    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9093",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return

    # 1. Sync Providers (VerifiedUser)
    providers = VerifiedUser.objects.all()
    print(f"📦 Found {providers.count()} Providers.")
    
    for user in providers:
        role = (user.role or "").lower()
        if role not in ['organization', 'individual', 'provider', 'organization_provider']:
            continue
            
        auth_id = str(user.auth_user_id)
        
        # Calculate Plan Capabilities
        try:
            caps = user.get_all_plan_capabilities() # Returns set of strings
            perms_list = list(caps)
            # Add CORE explicitly if missing
            if 'VETERINARY_CORE' not in perms_list:
                perms_list.append('VETERINARY_CORE')
        except Exception as e:
            print(f"⚠️ Error calculating perms for Provider {auth_id}: {e}")
            perms_list = []

        payload_perms = [{"service_key": p} for p in perms_list]

        event = {
            "service": "provider_service",
            "event_type": "USER_PERMISSIONS_SYNCED",
            "data": {
                "auth_user_id": auth_id,
                "role": role, # Important for Consumer to trigger Clinic update
                "permissions": payload_perms
            },
            "timestamp": int(time.time())
        }
        
        print(f"🔄 Syncing Provider {user.full_name} ({auth_id}): {len(payload_perms)} capabilities")
        producer.send("service_provider_events", value=event)

    # 2. Sync Employees
    employees = OrganizationEmployee.objects.all()
    print(f"📦 Found {employees.count()} Employees.")
    
    for emp in employees:
        auth_id = str(emp.auth_user_id)
        role = (emp.role or "employee").lower()
        
        try:
            perms_list = emp.get_final_permissions()
        except Exception as e:
            print(f"⚠️ Error calculating perms for Employee {auth_id}: {e}")
            perms_list = []
        
        payload_perms = [{"service_key": p} for p in perms_list]
        
        event = {
            "service": "provider_service",
            "event_type": "USER_PERMISSIONS_SYNCED",
            "data": {
                "auth_user_id": auth_id,
                "role": role,
                "permissions": payload_perms
            },
            "timestamp": int(time.time())
        }
        
        print(f"🔄 Syncing Employee {emp.full_name} ({auth_id}): {len(payload_perms)} capabilities")
        producer.send("service_provider_events", value=event)

    producer.flush()
    print("✅ Force Sync Complete.")

if __name__ == "__main__":
    force_sync()
