import os
import django
import sys
import json
import time

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_provider_service.settings')
django.setup()

from kafka import KafkaProducer
from django.conf import settings
# USE THE CORRECT MODEL
from service_provider.models import OrganizationEmployee

def sync_permissions():
    print("🚀 Starting Permission Sync Repair...")
    
    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9093",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return

    employees = OrganizationEmployee.objects.all()
    print(f"📦 Found {employees.count()} employees to sync.")

    for emp in employees:
        # OrganizationEmployee has auth_user_id (UUID), convert to string
        auth_id = str(emp.auth_user_id)
        
        # Calculate Final Permissions
        try:
            perms_list = emp.get_final_permissions()
        except Exception as e:
            print(f"⚠️ Error calculating perms for {auth_id}: {e}")
            perms_list = []
        
        # Format for Veterinary Service Consumer: [{ "service_key": "VETERINARY_VISITS" }]
        payload_perms = [{"service_key": p} for p in perms_list]

        if not payload_perms:
            print(f"⚠️ No perms for {auth_id}, skipping sync.")
            continue

        event = {
            "service": "provider_service",
            "event_type": "USER_PERMISSIONS_SYNCED",
            "data": {
                "auth_user_id": auth_id,
                "permissions": payload_perms
            },
            "timestamp": int(time.time())
        }
        
        # Attempt to get name if possible
        name = emp.full_name or "Unknown"
        print(f"🔄 Syncing {name} ({auth_id}): {len(payload_perms)} capabilities")
        producer.send("service_provider_events", value=event)
    
    producer.flush()
    print("✅ Sync Complete.")

if __name__ == "__main__":
    sync_permissions()
