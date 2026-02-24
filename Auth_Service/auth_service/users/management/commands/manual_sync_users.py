
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.kafka_producer import publish_event
import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Sync all users to Kafka for cross-service consistency'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting Manual Sync of ALL Users...'))
        
        users = User.objects.filter(is_active=True)
        count = users.count()
        self.stdout.write(f"📦 Found {count} ACTIVE users in Auth Service.")

        for i, user in enumerate(users):
            msg = f"[{i+1}/{count}] Syncing {user.email} ({user.role})"
            self.stdout.write(msg)
            
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

            # 1. Publish USER_UPDATED (Update existing records)
            try:
                publish_event("USER_UPDATED", payload)
                time.sleep(0.05) 
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to sync {user.email}: {e}"))

        self.stdout.write(self.style.SUCCESS('\n✅ Sync Complete!'))
