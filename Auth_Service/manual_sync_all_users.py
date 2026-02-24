import os
import django
import sys
import time

# Setup Auth Service environment
sys.path.append("/Users/PraveenWorks/Anil Works/PetLeo-Backend/Auth_Service")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
django.setup()

from users.models import User
from users.kafka_producer import publish_event

def sync_all_users():
    print("🚀 Starting Manual Sync of ALL Users...")
    users = User.objects.all()
    count = users.count()
    print(f"📦 Found {count} users in Auth Service.")

    for i, user in enumerate(users):
        print(f"[{i+1}/{count}] Syncing {user.email} ({user.role})")
        
        # Construct payload
        payload = {
            "auth_user_id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role.name if hasattr(user.role, 'name') else str(user.role),
            "avatar_url": user.avatar_url,
            "is_active": user.is_active
        }

        # 1. Publish USER_UPDATED
        publish_event("USER_UPDATED", payload)
        
        # 2. Publish USER_VERIFIED (to ensure activation)
        if user.is_active:
            publish_event("USER_VERIFIED", payload)

        time.sleep(0.1) # Prevent flooding

    print("\n✅ Sync Complete!")

if __name__ == "__main__":
    sync_all_users()
